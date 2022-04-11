from rest_framework import permissions


class PermissionsDebug(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        print(f'PERM CHECK: req:{request} view:{view} obj:{obj}')
        return True

