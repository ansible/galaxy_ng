from rest_framework.permissions import BasePermission, SAFE_METHODS


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
        if request.method in SAFE_METHODS:
            return True
        # Otherwise, deny access
        return False
