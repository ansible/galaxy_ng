from django.conf import settings
from rest_framework.permissions import BasePermission, SAFE_METHODS

from ansible_base.rbac.api.permissions import AnsibleBaseUserPermissions
from galaxy_ng.app.models.auth import User


class IsSuperUserOrReadOnly(BasePermission):
    """
    Custom permission to grant full access to superusers and
    read-only access to non-superusers.
    """

    def has_permission(self, request, view):
        # Allow full access if the user is a superuser
        if request.user and request.user.is_superuser:
            return True
        # Allow read-only access (GET, HEAD, OPTIONS) for other users
        if request.method in SAFE_METHODS:  # noqa: SIM103
            return True
        # Otherwise, deny access
        return False


class ComplexUserPermissions(AnsibleBaseUserPermissions):
    """
    ComplexUserPermissions complies with the "complex" requirements
    of a system where there is a resource server that syncs users
    and a jwt that creates users and a confusing mix of how is_superuser
    can get populated on galaxy when the resource server is configured,

    To try to break down the logic when the resource server is configured:
        - users CAN NOT be created/edited/deleted directly in galaxy, except ...
        - if the request is a PATCH or a PUT that is only modifying the value
          of is_superuser, then it can be allowed
        - if the caller is a superuser, they can set the is_superuser flag for
          a user to True or False
        - if the caller is the user being modified, they can only set the flag
          to False
        - No user can be demoted from superuser when they are the last superuser

    Note: this is only designed to work for the _ui/v2/users/ viewset.
    """

    def has_permission(self, request, view):
        if (
            request.user.is_superuser
            and not settings.get('IS_CONNECTED_TO_RESOURCE_SERVER')
        ):
            return True

        if (
            request.method not in ('GET', 'HEAD', 'PUT', 'PATCH')
            and settings.get('IS_CONNECTED_TO_RESOURCE_SERVER')
        ):
            return False

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        if (
            request.user.is_superuser
            and not settings.get('IS_CONNECTED_TO_RESOURCE_SERVER')
        ):
            return True

        # these can be modified ... kinda
        allowed_fields = ['is_superuser']

        # these are ignored in the serializer
        ignored_fields = [
            'groups',
            'teams',
            'organizations',
            'date_joined',
            'resource',
            'auth_provider',
            'model_permissions'
        ]

        # compare new data vs current object data
        for field, value in request.data.items():

            if field in ignored_fields:
                continue

            if getattr(obj, field) == value:
                continue

            if field not in allowed_fields:
                return False

        # we can't allow the last superuser to get demoted
        if (
            request.data.get('is_superuser') is False
            and User.objects.filter(is_superuser=True).count() == 1
            and obj.is_superuser
        ):
            return False

        # superuser can set the value to True or False
        if request.user.is_superuser:
            return True

        # user can set themself only to False
        if request.user == obj and request.data.get('is_superuser') is False:  # noqa: SIM103
            return True

        return False
