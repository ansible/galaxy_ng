import base64
import json
import logging

from django.conf import settings
from django.db import transaction


from pulp_ansible.app.models import AnsibleRepository
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

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
        identity = header.get("identity")
        if identity is None:
            raise AuthenticationFailed

        identity_type = identity.get("type", "User")
        if identity_type == "User":
            try:
                identity = header['identity']
                account = identity['account_number']

                user = identity['user']
                username = user['username']
            except KeyError:
                raise AuthenticationFailed
        elif identity_type == "ServiceAccount":
            try:
                service_account = identity['service_account']
                # service-account-<uuid4> is too long for the username field
                username = service_account['username'].replace('service-account-', '')
                # make this the same?
                account = username
                # all other attributes for service accounts is null
                user = {}
            except KeyError:
                raise AuthenticationFailed
        else:
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

        return user, {'rh_identity': header}

    def _ensure_group(self, account_scope, account):
        """Create a auto group for the account"""

        with transaction.atomic():
            group, created = Group.objects.get_or_create_identity(account_scope, account)
        return group, created

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
    def _decode_header(raw):
        try:
            json_string = base64.b64decode(raw)
            return json.loads(json_string)
        except ValueError:
            raise AuthenticationFailed
