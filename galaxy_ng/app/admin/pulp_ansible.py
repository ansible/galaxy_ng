# -*- coding: utf-8 -*-
from django.contrib import admin

from .base import BaseModelAdmin, PulpModelAdmin

from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionImport,
    CollectionRemote,
    CollectionVersion,
    Role,
    RoleRemote,
    Tag,
)


@admin.register(Role)
class RoleAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
        "pulp_type",
        "namespace",
        "name",
        "version",
    )
    list_filter = ("pulp_created", "pulp_last_updated")
    search_fields = ("name",)


@admin.register(Collection)
class CollectionAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
        "namespace",
        "name",
        # "deprecated",
    )
    list_filter = ("pulp_created", "pulp_last_updated",
                   # "deprecated",
                   )
    search_fields = (
        "namespace",
        "name",
    )


@admin.register(CollectionImport)
class CollectionImportAdmin(BaseModelAdmin):
    readonly_fields = ("task", "messages")
    list_display = ("task", "messages")
    fields = ("task", "messages")


@admin.register(Tag)
class TagAdmin(PulpModelAdmin):
    list_display = (
        "name",
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
    )
    list_filter = ("pulp_created", "pulp_last_updated")
    search_fields = ("name",)


@admin.register(CollectionVersion)
class CollectionVersionAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "namespace",
        "name",
        "version",
        "description",
        "pulp_type",
        "is_highest",
        "pulp_last_updated",
        "pulp_created",
    )
    list_filter = ("pulp_created", "pulp_last_updated", "is_highest")
    raw_id_fields = ("tags",)
    search_fields = ("namespace", "name", "pulp_id", "collection")

    readonly_fields = (
        "namespace",
        "name",
        "version",
        "is_highest",
        "collection",
        "authors",
        "contents",
        "dependencies",
        "description",
        "homepage",
        "issues",
        "license",
        "docs_blob",
        "documentation",
        "repository",
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
    )
    fields = (
        "pulp_id",
        "namespace",
        "name",
        "version",
        "is_highest",
        "description",
        "dependencies",
        "authors",
        "homepage",
        "issues",
        "repository",
        "license",
        "contents",
        "pulp_type",
        "documentation",
        "docs_blob",
        "search_vector",
        "pulp_created",
        "pulp_last_updated",
    )


@admin.register(RoleRemote)
class RoleRemoteAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
        "pulp_type",
        "name",
        "url",
        # 'ca_cert',
        "client_cert",
        "client_key",
        "tls_validation",
        "username",
        "password",
        "proxy_url",
        "download_concurrency",
        "policy",
    )
    list_filter = ("pulp_created", "pulp_last_updated", "tls_validation")
    search_fields = ("name",)


@admin.register(AnsibleRepository)
class AnsibleRepositoryAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
        "pulp_type",
        "name",
        "description",
        "next_version",
    )
    list_filter = ("pulp_created", "pulp_last_updated")
    search_fields = ("name",)


@admin.register(CollectionRemote)
class CollectionRemoteAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
        "pulp_type",
        "name",
        "url",
        # 'ca_cert',
        # 'client_cert',
        # 'client_key',
        "tls_validation",
        "username",
        "password",
        "proxy_url",
        "download_concurrency",
        "policy",
        "requirements_file",
        "auth_url",
        "token",
    )

    list_filter = ("pulp_created", "pulp_last_updated", "tls_validation")
    search_fields = ("name",)


@admin.register(AnsibleDistribution)
class AnsibleDistributionAdmin(PulpModelAdmin):
    list_display = (
        "pulp_id",
        "pulp_created",
        "pulp_last_updated",
        "pulp_type",
        "name",
        "base_path",
        "content_guard",
        "remote",
        "repository",
        "repository_version",
    )
    list_filter = (
        "pulp_created",
        "pulp_last_updated",
        "content_guard",
        "remote",
        "repository",
        "repository_version",
    )
    search_fields = ("name",)
