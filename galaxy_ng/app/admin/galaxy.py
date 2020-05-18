# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse
from django.utils.html import format_html

from .base import BaseModelAdmin

from galaxy_ng.app.models import (
    User,
    Group,
    Namespace,
    NamespaceLink,
    CollectionImport,
    SyncList,
    CollectionSyncTask,
    ContainerDistribution,
    ContainerDistroReadme,
    ContainerRegistryRemote,
    ContainerRegistryRepos,
    ContainerNamespace,
    ContainerSyncTask,
)


@admin.register(ContainerDistribution)
class ContainerDistributionAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'name',
        'base_path',
        'content_guard',
        'remote',
        'basedistribution_ptr',
        'repository',
        'repository_version',
        'namespace',
        'private',
        'description',
    )
    list_filter = (
        'pulp_created',
        'pulp_last_updated',
        'content_guard',
        'remote',
        'basedistribution_ptr',
        'repository',
        'repository_version',
        'namespace',
        'private',
    )
    search_fields = ('name',)


@admin.register(ContainerNamespace)
class ContainerNamespaceAdmin(admin.ModelAdmin):
    list_display = ('pulp_id', 'pulp_created', 'pulp_last_updated', 'name')
    list_filter = ('pulp_created', 'pulp_last_updated')
    search_fields = ('name',)


@admin.register(ContainerDistroReadme)
class ContainerDistroReadmeAdmin(admin.ModelAdmin):
    list_display = ('container', 'created', 'updated', 'text')
    list_filter = ('container', 'created', 'updated')


@admin.register(ContainerRegistryRemote)
class ContainerRegistryRemoteAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'name',
        'url',
        'ca_cert',
        'client_cert',
        'client_key',
        'tls_validation',
        'username',
        'password',
        'proxy_url',
        'proxy_username',
        'proxy_password',
        'download_concurrency',
        'policy',
        'total_timeout',
        'connect_timeout',
        'sock_connect_timeout',
        'sock_read_timeout',
        'headers',
        'rate_limit',
    )
    list_filter = ('pulp_created', 'pulp_last_updated', 'tls_validation')
    search_fields = ('name',)


@admin.register(ContainerRegistryRepos)
class ContainerRegistryReposAdmin(admin.ModelAdmin):
    list_display = ('registry', 'repository_remote')
    list_filter = ('registry', 'repository_remote')


@admin.register(ContainerSyncTask)
class ContainerSyncTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'repository', 'task')
    list_filter = ('repository', 'task')


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
    search_fields = ['name', 'company', 'email']


@admin.register(NamespaceLink)
class NamespaceLinkAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'url', 'namespace')
    list_filter = ('namespace',)
    search_fields = ['namespace__name', 'namespace__company', 'name', 'url']


@admin.register(CollectionImport)
class CollectionImportAdmin(BaseModelAdmin):
    list_display = ('label_and_version', 'task_id', 'created_at', 'label',
                    'namespace', 'name', 'version')
    list_display_links = ('label_and_version', 'task_id', 'created_at')
    list_filter = ('created_at', 'namespace')
    raw_fields = ('namespace', 'name', 'version', 'task_id', 'created_at')
    read_only_fields = ('namespace', 'name', 'version', 'task_id', 'created_at')
    search_fields = ('name', 'namespace')
    date_hierarchy = 'created_at'


@admin.register(CollectionSyncTask)
class CollectionSyncTaskAdmin(BaseModelAdmin):
    pass


class SyncListCollectionsInline(admin.StackedInline):
    model = SyncList.collections.through


class SyncListNamespacesInline(admin.StackedInline):
    model = SyncList.namespaces.through


@admin.register(SyncList)
class SyncListAdmin(BaseModelAdmin):
    list_display = ('id', 'name', 'policy', 'view_repository_link', 'view_upstream_repository_link')
    list_display_links = ('id', 'name', 'policy',
                          'view_repository_link', 'view_upstream_repository_link')
    search_fields = ('name',)

    def view_repository_link(self, obj):
        url = reverse("admin:ansible_ansiblerepository_change", args=(obj.repository.pulp_id,))
        return format_html('<a href="{}">{}</a>', url, obj.repository)
    view_repository_link.short_description = "Repository"

    def view_upstream_repository_link(self, obj):
        url = reverse("admin:ansible_ansiblerepository_change",
                      args=(obj.upstream_repository.pulp_id,))
        return format_html('<a href="{}">{}</a>', url, obj.repository)
    view_repository_link.short_description = "Upstream Rep"
