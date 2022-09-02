import json
import re

from rest_framework import serializers
from django.core import exceptions
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from pulpcore.plugin.util import get_users_with_perms

from pulp_container.app import models as container_models
from pulp_container.app import serializers as container_serializers
from pulpcore.plugin import models as core_models
from pulpcore.plugin import serializers as core_serializers

from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import GroupPermissionField, MyPermissionsField
from galaxy_ng.app.api import utils

namespace_fields = ("name", "my_permissions", "owners")

VALID_REMOTE_REGEX = r"^[A-Za-z0-9._-]*/?[A-Za-z0-9._-]*$"


class ContainerNamespaceSerializer(serializers.ModelSerializer):
    my_permissions = MyPermissionsField(source="*", read_only=True)
    owners = serializers.SerializerMethodField()

    class Meta:
        model = models.ContainerNamespace
        fields = namespace_fields
        read_only_fields = (
            "name",
            "my_permissions",
        )

    @extend_schema_field(serializers.ListField)
    def get_owners(self, namespace):
        return get_users_with_perms(
            namespace, with_group_users=False, for_concrete_model=True
        ).values_list("username", flat=True)


class ContainerNamespaceDetailSerializer(ContainerNamespaceSerializer):
    groups = GroupPermissionField()

    class Meta:
        model = models.ContainerNamespace
        fields = namespace_fields + ("groups",)
        read_only_fields = (
            "name",
            "my_permissions",
        )


class ContainerRepositorySerializer(serializers.ModelSerializer):
    pulp = serializers.SerializerMethodField()
    namespace = ContainerNamespaceSerializer()
    id = serializers.SerializerMethodField()
    created = serializers.SerializerMethodField()
    updated = serializers.SerializerMethodField()

    # This serializer is purposfully refraining from using pulp fields directly
    # in the top level response body. This is because future versions of hub will have to
    # support indexing other registries and the API responses for a container
    # repository should make sense for containers hosted by pulp and containers
    # hosted by other registries.
    class Meta:
        model = models.ContainerDistribution
        read_only_fields = (
            "id",
            "name",
            # this field will return null on instances where hub is indexing a
            # different repo
            "pulp",
            "namespace",
            "description",
            "created",
            "updated",
        )

        fields = read_only_fields

    def get_namespace(self, distro) -> str:
        return distro.namespace.name

    @extend_schema_field(OpenApiTypes.UUID)
    def get_id(self, distro):
        return distro.pk

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_created(self, distro):
        return distro.repository.pulp_created

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_updated(self, distro):
        return distro.repository.pulp_last_updated

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_pulp(self, distro):
        repo = distro.repository
        remote = None
        if repo.remote:
            remote = ContainerRemoteSerializer(repo.remote.cast()).data

        sign_state = repo.content.filter(
            pulp_type="container.signature"
        ).count() > 0 and "signed" or "unsigned"

        return {
            "repository": {
                "pulp_id": repo.pk,
                "pulp_type": repo.pulp_type,
                "version": repo.latest_version().number,
                "name": repo.name,
                "description": repo.description,
                "pulp_created": repo.pulp_created,
                "pulp_labels": {label.key: label.value for label in repo.pulp_labels.all()},
                "remote": remote,
                "sign_state": sign_state
            },
            "distribution": {
                "pulp_id": distro.pk,
                "name": distro.name,
                "pulp_created": distro.pulp_created,
                "base_path": distro.base_path,
                "pulp_labels": {label.key: label.value for label in distro.pulp_labels.all()},
            },
        }


class ManifestListManifestSerializer(serializers.ModelSerializer):
    digest = serializers.SerializerMethodField()

    class Meta:
        model = container_models.ManifestListManifest
        fields = (
            "os",
            "architecture",
            "os_version",
            "os_features",
            "features",
            "variant",
            "digest"
        )

    def get_digest(self, obj):
        return obj.manifest_list.digest


class ContainerManifestSerializer(serializers.ModelSerializer):
    config_blob = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    layers = serializers.SerializerMethodField()
    image_manifests = ManifestListManifestSerializer(many=True)

    class Meta:
        model = container_models.Manifest
        fields = (
            "pulp_id",
            "digest",
            "schema_version",
            "media_type",
            "config_blob",
            "tags",
            "pulp_created",
            "layers",
            "image_manifests"
        )

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_layers(self, obj):
        layers = []
        # use the prefetched blob_list and artifact_list instead of obj.blobs and
        # blob._artifacts to cut down on queries made.
        for blob in obj.blob_list:
            # Manifest can be empty after deleting an image.
            if blob.artifact_list:
                layers.append(
                    {"digest": blob.digest, "size": blob.artifact_list[0].size}
                )
        return layers

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_config_blob(self, obj):
        if not obj.config_blob:
            return {}
        return {"digest": obj.config_blob.digest}

    @extend_schema_field(serializers.ListField)
    def get_tags(self, obj):
        tags = []
        # tagget_manifests returns all tags on the manifest, not just the ones
        # that are in the latest version of the repo.
        for tag in obj.tagged_manifests.all():
            tags.append(tag.name)

        return tags


class ManifestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = container_models.Manifest
        fields = (
            "pulp_id",
            "digest",
            "schema_version",
            "media_type",
            "pulp_created",
        )


class ContainerTagSerializer(serializers.ModelSerializer):
    tagged_manifest = ManifestListSerializer()

    class Meta:
        model = container_models.Tag
        fields = (
            "name",
            "pulp_created",
            "pulp_last_updated",
            "tagged_manifest"
        )


class ContainerManifestDetailSerializer(ContainerManifestSerializer):
    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_config_blob(self, obj):
        with obj.config_blob._artifacts.first().file.open() as f:
            config_json = json.load(f)

        return {
            "digest": obj.config_blob.digest,
            "data": config_json,
        }


class ContainerRepositoryHistorySerializer(serializers.ModelSerializer):
    added = serializers.SerializerMethodField()
    removed = serializers.SerializerMethodField()

    class Meta:
        model = core_models.RepositoryVersion
        fields = ("pulp_id", "added", "removed", "pulp_created", "number")

    @extend_schema_field(serializers.ListField(child=serializers.JSONField()))
    def get_added(self, obj):
        return [self._content_info(content.content) for content in obj.added_memberships.all()]

    @extend_schema_field(serializers.ListField(child=serializers.JSONField()))
    def get_removed(self, obj):
        return [self._content_info(content.content) for content in obj.removed_memberships.all()]

    def _content_info(self, content):
        return_data = {
            "pulp_id": content.pk,
            "pulp_type": content.pulp_type,
            "manifest_digest": None,
            "tag_name": None,
        }

        # TODO: Figure out if there is a way to prefetch Manifest and Tag objects
        if content.pulp_type == "container.manifest":
            manifest = container_models.Manifest.objects.get(pk=content.pk)
            return_data["manifest_digest"] = manifest.digest
        elif content.pulp_type == "container.tag":
            tag = container_models.Tag.objects.select_related("tagged_manifest").get(pk=content.pk)
            return_data["manifest_digest"] = tag.tagged_manifest.digest
            return_data["tag_name"] = tag.name

        return return_data


class ContainerReadmeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ContainerDistroReadme
        fields = (
            "updated",
            "created",
            "text",
        )

        read_only_fields = (
            "updated",
            "created",
        )


class ContainerRegistryRemoteSerializer(
    core_serializers.RemoteSerializer,
):
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    last_sync_task = utils.RemoteSyncTaskField(source="*")
    write_only_fields = serializers.SerializerMethodField()
    is_indexable = serializers.SerializerMethodField()

    class Meta:
        model = models.ContainerRegistryRemote
        fields = [
            "pk",
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


class ContainerRemoteSerializer(
    container_serializers.ContainerRemoteSerializer,
):
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
            "pulp_id",
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
