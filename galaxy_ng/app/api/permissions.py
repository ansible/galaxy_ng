from rest_framework.permissions import BasePermission, SAFE_METHODS

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import SYSTEM_SCOPE


class IsPartnerEngineer(BasePermission):
    """Checks if user is in partner engineers group."""

    GROUP_NAME = f'{SYSTEM_SCOPE}:partner-engineers'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.groups.filter(name=self.GROUP_NAME).exists()


class IsNamespaceOwner(BasePermission):
    """Checks if user is in namespace owners group."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if isinstance(obj, Namespace):
            namespace = obj
        elif hasattr(obj, 'namespace'):
            namespace = obj.namespace
        else:
            obj_type = type(obj).__name__
            raise RuntimeError(
                f"Object {obj_type} is not a Namespace and does"
                f" not have \"namespace\" attribute. "
            )

        return namespace.groups.filter(pk__in=request.user.groups.all()).exists()


class IsNamespaceOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return IsNamespaceOwner().has_object_permission(request, view, obj)


class IsNamespaceOwnerOrPartnerEngineer(BasePermission):
    """Checks if user is owner of namespace or a partner engineer."""

    def has_object_permission(self, request, view, obj):
        if IsPartnerEngineer().has_permission(request, view):
            return True
        return IsNamespaceOwnerOrReadOnly().has_object_permission(
            request, view, obj)
