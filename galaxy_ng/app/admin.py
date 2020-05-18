# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import Permission
from django.contrib.auth.hashers import make_password, check_password

from pulpcore.plugin.admin import BaseModelAdmin

from .models import User, Group, Namespace, NamespaceLink, CollectionImport, SyncList


@admin.register(User)
class UserAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'password',
        'last_login',
        'is_superuser',
        'username',
        'first_name',
        'last_name',
        'email',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'last_login',
        'is_superuser',
        'is_staff',
        'is_active',
        'date_joined',
    )
    raw_id_fields = ('groups', 'user_permissions')

    def save_model(self, request, obj, form, change):
        user_database = User.objects.get(pk=obj.pk)
        # Check firs the case in which the password is not encoded,
        # then check in the case that the password is encode
        if not (check_password(form.data['password'], user_database.password)
                or user_database.password == form.data['password']):
            obj.password = make_password(obj.password)
        else:
            obj.password = user_database.password
        super().save_model(request, obj, form, change)


@admin.register(Group)
class GroupAdmin(BaseModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Namespace)
class NamespaceAdmin(BaseModelAdmin):
    list_display = (
        'id',
        'name',
        'company',
        'email',
        'avatar_url',
        'description',
        'resources',
    )
    raw_id_fields = ('groups',)
    search_fields = ['groups__name', 'name', 'company', 'email']
    autocomplete_fields = ['groups']


@admin.register(NamespaceLink)
class NamespaceLinkAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'url', 'namespace')
    list_filter = ('namespace',)
    search_fields = ['namespace__name', 'namespace__company', 'name', 'url']


@admin.register(CollectionImport)
class CollectionImportAdmin(BaseModelAdmin):
    list_display = ('task_id', 'created_at', 'namespace', 'name', 'version')
    list_filter = ('created_at', 'namespace')
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(Permission)
class PermissionAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'content_type', 'codename')
    raw_id_fields = ('content_type',)
    search_fields = ('name', 'content_type__app_label', 'content_type__model', 'codename')


@admin.register(SyncList)
class SyncListAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'policy', 'repository')
    raw_id_fields = ('groups', 'users', 'collections', 'namespaces')
    search_fields = ('name',)
