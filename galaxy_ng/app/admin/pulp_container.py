# -*- coding: utf-8 -*-
from django.contrib import admin

from pulp_container.app.models import (
    Blob,
    Manifest,
    BlobManifest,
    ManifestListManifest,
    Tag,
    ContainerNamespace,
    ContainerRepository,
    ContainerPushRepository,
    ContainerRemote,
    ContainerDistribution,
    Upload,
    ContentRedirectContentGuard,
)


@admin.register(Blob)
class BlobAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'upstream_id',
        'digest',
        'media_type',
    )
    list_filter = ('pulp_created', 'pulp_last_updated')


@admin.register(Manifest)
class ManifestAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'upstream_id',
        'digest',
        'schema_version',
        'media_type',
        'config_blob',
    )
    list_filter = ('pulp_created', 'pulp_last_updated', 'config_blob')
    raw_id_fields = ('blobs', 'listed_manifests')


@admin.register(BlobManifest)
class BlobManifestAdmin(admin.ModelAdmin):
    list_display = ('id', 'manifest', 'manifest_blob')
    list_filter = ('manifest', 'manifest_blob')


@admin.register(ManifestListManifest)
class ManifestListManifestAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'architecture',
        'os',
        'os_version',
        'os_features',
        'features',
        'variant',
        'image_manifest',
        'manifest_list',
    )
    list_filter = ('image_manifest', 'manifest_list')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'upstream_id',
        'name',
        'tagged_manifest',
    )
    list_filter = ('pulp_created', 'pulp_last_updated', 'tagged_manifest')
    search_fields = ('name',)


@admin.register(ContainerNamespace)
class ContainerNamespaceAdmin(admin.ModelAdmin):
    list_display = ('pulp_id', 'pulp_created', 'pulp_last_updated', 'name')
    list_filter = ('pulp_created', 'pulp_last_updated')
    search_fields = ('name',)


@admin.register(ContainerRepository)
class ContainerRepositoryAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'name',
        'description',
        'next_version',
        'remote',
    )
    list_filter = ('pulp_created', 'pulp_last_updated', 'remote')
    search_fields = ('name',)


@admin.register(ContainerPushRepository)
class ContainerPushRepositoryAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'name',
        'description',
        'next_version',
        'remote',
    )
    list_filter = ('pulp_created', 'pulp_last_updated', 'remote')
    search_fields = ('name',)


@admin.register(ContainerRemote)
class ContainerRemoteAdmin(admin.ModelAdmin):
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
        'upstream_name',
        'include_foreign_layers',
        'include_tags',
        'exclude_tags',
    )
    list_filter = (
        'pulp_created',
        'pulp_last_updated',
        'tls_validation',
        'include_foreign_layers',
    )
    search_fields = ('name',)


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
        'repository',
        'repository_version',
        'namespace',
        'private',
    )
    search_fields = ('name',)


@admin.register(Upload)
class UploadAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'size',
        'repository',
    )
    list_filter = ('pulp_created', 'pulp_last_updated', 'repository')


@admin.register(ContentRedirectContentGuard)
class ContentRedirectContentGuardAdmin(admin.ModelAdmin):
    list_display = (
        'pulp_id',
        'pulp_created',
        'pulp_last_updated',
        'pulp_type',
        'name',
        'description',
        'shared_secret',
    )
    list_filter = ('pulp_created', 'pulp_last_updated')
    search_fields = ('name',)
