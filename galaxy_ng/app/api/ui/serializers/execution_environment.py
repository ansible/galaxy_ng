import re

from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.core import exceptions
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from pulpcore.plugin import serializers as core_serializers

from pulp_container.app import models as container_models
from pulp_container.app import serializers as container_serializers

from galaxy_ng.app import models
from galaxy_ng.app.api import utils

namespace_fields = ("name", "my_permissions", "owners")

VALID_REMOTE_REGEX = r"^[A-Za-z0-9._-]*/?[A-Za-z0-9._-]*$"


class ContainerRemoteSerializer(
    container_serializers.ContainerRemoteSerializer,
):
    id = serializers.UUIDField(source='pulp_id', required=False, read_only=True)
    created_at = serializers.DateTimeField(source='pulp_created', read_only=True, required=False)
    updated_at = serializers.DateTimeField(
        source='pulp_last_updated', read_only=True, required=False)
    registry = serializers.CharField(source="registry.registry.pk")
    last_sync_task = utils.RemoteSyncTaskField(source="*")

    class Meta:
        read_only_fields = (
            "created_at",
            "updated_at",
            "name"
        )

        model = container_models.ContainerRemote
        extra_kwargs = {
            'name': {'read_only': True},
            'client_key': {'write_only': True},
        }

        fields = [
            "id",
            "pulp_href",
            "name",
            "upstream_name",
            "registry",
            "last_sync_task",
            "created_at",
            "updated_at",
            "include_foreign_layers",
            "include_tags",
            "exclude_tags"
        ]

    def validate_registry(self, value):
        try:
            registry = models.ContainerRegistryRemote.objects.get(pk=value)
            return registry
        except exceptions.ObjectDoesNotExist:
            raise serializers.ValidationError(_("Selected registry does not exist."))

    # pulp container doesn't validate container names and I don't know what is considered a
    # valid name.This is a stopgap solution to make sure that at the very least, users
    # don't create names that breakthe galaxy_ng registry
    def validate_name(self, value):
        r = re.compile(VALID_REMOTE_REGEX)
        if not r.match(value):
            raise serializers.ValidationError(
                _('Container names can only contain alphanumeric numbers, '
                    '".", "_", "-" and a up to one "/".'))
        return value

    @transaction.atomic
    def update(self, instance, validated_data):

        registry = validated_data['registry']['registry']['pk']
        del validated_data['registry']

        # Ensure connection exists between remote and registry
        models.container.ContainerRegistryRepos.objects.get_or_create(
            repository_remote=instance,
            defaults={'registry': registry, 'repository_remote': instance}
        )

        if (instance.name != validated_data['name']):
            raise serializers.ValidationError(detail={
                "name": _("Name cannot be changed.")
            })

        instance.registry.registry = registry
        instance.registry.save()
        validated_data = {**registry.get_connection_fields(), **validated_data}
        return super().update(instance, validated_data)

    @transaction.atomic
    def create(self, validated_data):
        registry = validated_data['registry']['registry']['pk']
        del validated_data['registry']

        validated_data = {**registry.get_connection_fields(), **validated_data}

        # Exclude source tags by default since they don't provide much value to customers and
        # can cause network issues when syncing.
        validated_data["exclude_tags"] = validated_data.get("exclude_tags", [])
        if "*-source" not in validated_data["exclude_tags"]:
            validated_data["exclude_tags"].append("*-source")

        request = self.context['request']

        # Create the remote instances using data from the registry

        remote = super().create(validated_data)
        remote_href = container_serializers.ContainerRemoteSerializer(
            remote, context={"request": request}).data['pulp_href']

        # Create the container repository with the new remote
        repo_serializer = container_serializers.ContainerRepositorySerializer(
            data={"name": remote.name, "remote": remote_href}, context={"request": request}
        )
        repo_serializer.is_valid(raise_exception=True)
        repository = repo_serializer.create(repo_serializer.validated_data)
        repo_href = container_serializers.ContainerRepositorySerializer(
            repository, context={"request": request}
        ).data["pulp_href"]

        # Create the container distribution with the new repository
        dist_serializer = container_serializers.ContainerDistributionSerializer(
            data={"base_path": remote.name, "name": remote.name, "repository": repo_href}
        )
        dist_serializer.is_valid(raise_exception=True)
        dist_serializer.create(dist_serializer.validated_data)

        # Bind the new remote to the registry object.
        models.ContainerRegistryRepos.objects.create(registry=registry, repository_remote=remote)

        return remote


class ContainerRegistryRemoteSerializer(
    core_serializers.RemoteSerializer,
):
    id = serializers.UUIDField(source='pk', required=False)
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    last_sync_task = utils.RemoteSyncTaskField(source="*")
    write_only_fields = serializers.SerializerMethodField()
    is_indexable = serializers.SerializerMethodField()

    class Meta:
        model = models.ContainerRegistryRemote
        fields = [
            "id",
            "pulp_href",
            "name",
            "url",
            "policy",
            "created_at",
            "updated_at",
            "username",
            "password",
            "tls_validation",
            "client_key",
            "client_cert",
            "ca_cert",
            "last_sync_task",
            "download_concurrency",
            "proxy_url",
            "proxy_username",
            "proxy_password",
            "write_only_fields",
            "rate_limit",
            "is_indexable"
        ]
        extra_kwargs = {
            'name': {'read_only': True},
            'client_key': {'write_only': True},
        }

    @extend_schema_field(serializers.ListField)
    def get_write_only_fields(self, obj):
        return utils.get_write_only_fields(self, obj)

    def get_is_indexable(self, obj) -> bool:
        if obj.get_registry_backend():
            return True
        return False
