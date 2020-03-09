import base64
import json

from django.conf import settings
from django.db import transaction
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from galaxy_ng.app.models.auth import Group, User


RH_ACCOUNT_SCOPE = 'rh-identity-account'


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

        group, _ = Group.objects.get_or_create_identity(RH_ACCOUNT_SCOPE, account)

        user = self._ensure_user(
            username,
            group,
            email=email,
            first_name=first_name,
            last_name=last_name
        )

        return user, {'rh_identity': header}

    @staticmethod
    def _ensure_user(username, group, **attrs):
        with transaction.atomic():
            user, created = User.objects.update_or_create(
                username=username,
                defaults=attrs,
            )
            if created:
                user.groups.add(group)
        return user

    @staticmethod
    def _decode_header(raw):
        try:
            json_string = base64.b64decode(raw)
            return json.loads(json_string)
        except ValueError:
            raise AuthenticationFailed


class RHEntitlementRequired(BasePermission):
    """
    Allows access if user has RedHat entitlement specified
    in RH_ENTITLEMENT_REQUIRED settings parameter.
    """

    def has_permission(self, request, view):
        if not isinstance(request.auth, dict):
            return False
        header = request.auth.get('rh_identity')
        if not header:
            return False
        entitlements = header.get('entitlements', {})
        entitlement = entitlements.get(settings.RH_ENTITLEMENT_REQUIRED, {})
        return entitlement.get('is_entitled', False)
