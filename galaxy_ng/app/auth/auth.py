import base64
import json
import logging

from django.conf import settings
from django.db import transaction

from pulpcore.plugin.util import get_objects_for_group

from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from galaxy_ng.app.models import SyncList
from galaxy_ng.app.models.auth import Group, User

DEFAULT_UPSTREAM_REPO_NAME = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
RH_ACCOUNT_SCOPE = 'rh-identity-account'
SYNCLIST_DEFAULT_POLICY = 'exclude'


log = logging.getLogger(__name__)


class RHIdentityAuthentication(BaseAuthentication):
    """
    Authenticates users based on RedHat identity header.

    For users logging in first time creates User record and
    Tenant record for user's account if it doesn't exist.
    """

    header = 'HTTP_X_RH_IDENTITY'

    def authenticate(self, request):
        """
        Authenticates user.

        Raises:
            AuthenticationFailed: If invalid identity header provided.
        """
        if self.header not in request.META:
            return None

        header = self._decode_header(request.META[self.header])

        try:
            identity = header['identity']
            account = identity['account_number']

            user = identity['user']
            username = user['username']
        except KeyError:
            raise AuthenticationFailed

        email = user.get('email', '')
        first_name = user.get('first_name', '')
        last_name = user.get('last_name', '')

        group, _ = self._ensure_group(RH_ACCOUNT_SCOPE, account)

        user = self._ensure_user(
            username,
            group,
            email=email,
            first_name=first_name,
            last_name=last_name
        )

        self._ensure_synclists(group)

        return user, {'rh_identity': header}

    def _ensure_group(self, account_scope, account):
        """Create a auto group for the account and create a synclist distribution"""

        with transaction.atomic():
            group, created = Group.objects.get_or_create_identity(account_scope, account)
        return group, created

    def _ensure_synclists(self, group):
        with transaction.atomic():
            # check for existing synclists

            synclists_owned_by_group = \
                get_objects_for_group(group, 'galaxy.view_synclist', SyncList.objects.all())
            if synclists_owned_by_group:
                return synclists_owned_by_group

            upstream_repository = self._get_upstream_repo(group, DEFAULT_UPSTREAM_REPO_NAME)

            distro_name = settings.GALAXY_API_SYNCLIST_NAME_FORMAT.format(
                account_name=group.account_number()
            )

            distribution = self._get_or_create_synclist_distribution(
                distro_name, upstream_repository
            )

            default_synclist, _ = SyncList.objects.get_or_create(
                name=distro_name,
                defaults={
                    "distribution": distribution,
                    "policy": SYNCLIST_DEFAULT_POLICY,
                },
            )

            default_synclist.groups = {group: ['galaxy.synclist_owner']}
            default_synclist.save()
        return default_synclist

    @staticmethod
    def _ensure_user(username, group, **attrs):
        with transaction.atomic():
            user, created = User.objects.update_or_create(
                username=username,
                defaults=attrs,
            )
            if group not in user.groups.all():
                user.groups.add(group)
        return user

    @staticmethod
    def _get_upstream_repo(group, repository_name):
        try:
            upstream_repo = AnsibleRepository.objects.get(name=repository_name)
        except AnsibleRepository.DoesNotExist as exc:
            log.exception(exc)
            raise

        return upstream_repo

    @staticmethod
    def _get_or_create_synclist_distribution(distro_name, upstream_repository):
        # Create a distro pointing to the upstream repository by default.
        # This distro will be updated to point to a synclist repo when the synclist
        # is populated.
        distro, _ = AnsibleDistribution.objects.get_or_create(
            name=distro_name, base_path=distro_name, repository=upstream_repository
        )
        return distro

    @staticmethod
    def _decode_header(raw):
        try:
            json_string = base64.b64decode(raw)
            return json.loads(json_string)
        except ValueError:
            raise AuthenticationFailed
