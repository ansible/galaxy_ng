# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.models import Permission

from .models import User, Group, Namespace, NamespaceLink, CollectionImport


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
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


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Namespace)
class NamespaceAdmin(admin.ModelAdmin):
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
class NamespaceLinkAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url', 'namespace')
    list_filter = ('namespace',)
    search_fields = ['namespace__name', 'namespace__company', 'name', 'url']


@admin.register(CollectionImport)
class CollectionImportAdmin(admin.ModelAdmin):
    list_display = ('task_id', 'created_at', 'namespace', 'name', 'version')
    list_filter = ('created_at', 'namespace')
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'content_type', 'codename')
    raw_id_fields = ('content_type',)
    search_fields = ('name', 'content_type__app_label', 'content_type__model', 'codename')


# @admin.register(ContentType)
# class ContentTypeAdmin(admin.ModelAdmin):
#     list_display = ('id', 'app_label', 'model')
