from django.contrib import admin

from guardian.models.models import (
    GroupObjectPermission,
    UserObjectPermission,
)


@admin.register(UserObjectPermission)
class UserObjectPermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "permission", "content_type", "object_pk", "user")
    list_filter = ("permission", "content_type", "user")


@admin.register(GroupObjectPermission)
class GroupObjectPermissionAdmin(admin.ModelAdmin):
    list_display = ("id", "permission", "content_type", "object_pk", "group")
    list_filter = ("permission", "content_type", "group")
