
from django.contrib import admin
from django.contrib.auth.models import Permission

from .base import BaseModelAdmin


@admin.register(Permission)
class PermissionAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'content_type', 'codename')
    raw_id_fields = ('content_type',)
    search_fields = ('name', 'content_type__app_label', 'content_type__model', 'codename')
