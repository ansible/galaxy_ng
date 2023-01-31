import json

from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from pulpcore.plugin.util import get_users_with_perms
from pulpcore.plugin.serializers import IdentityField

from pulp_container.app import models as container_models
from pulpcore.plugin import models as core_models

from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import MyPermissionsField

from galaxy_ng.app.api.ui import serializers as ui_serializers

namespace_fields = ("id", "pulp_href", "name", "my_permissions",
                    "owners", "created_at", "updated_at")

VALID_REMOTE_REGEX = r"^[A-Za-z0-9._-]*/?[A-Za-z0-9._-]*$"


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


class ContainerNamespaceSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="pulp_id")
    pulp_href = IdentityField(view_name="pulp_container/namespaces-detail")
    my_permissions = MyPermissionsField(source="*", read_only=True)
    owners = serializers.SerializerMethodField()

    created_at = serializers.DateTimeField(source="pulp_created")
    updated_at = serializers.DateTimeField(source="pulp_last_updated")

    class Meta:
        model = models.ContainerNamespace
        fields = namespace_fields
        read_only_fields = (
            "id",
            "pulp_href",
            "name",
            "my_permissions"
        )

    @extend_schema_field(serializers.ListField)
    def get_owners(self, namespace):
        return get_users_with_perms(
            namespace, with_group_users=False, for_concrete_model=True
        ).values_list("username", flat=True)


class ContainerRepositorySerializer(serializers.ModelSerializer):
    pulp = serializers.SerializerMethodField()
    namespace = ContainerNamespaceSerializer()
    id = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    pulp_href = IdentityField(view_name='distributions-container/container-detail')

    # This serializer is purposfully refraining from using pulp fields directly
    # in the top level response body. This is because future versions of hub will have to
    # support indexing other registries and the API responses for a container
    # repository should make sense for containers hosted by pulp and containers
    # hosted by other registries.
    class Meta:
        model = models.ContainerDistribution
        read_only_fields = (
            "id",
            "pulp_href",
            "name",
            # this field will return null on instances where hub is indexing a
            # different repo
            "pulp",
            "namespace",
            "description",
            "created_at",
            "updated_at",
        )

        fields = read_only_fields

    def get_namespace(self, distro) -> str:
        return distro.namespace.name

    @extend_schema_field(OpenApiTypes.UUID)
    def get_id(self, distro):
        return distro.pk

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_created_at(self, distro):
        return distro.repository.pulp_created

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_updated_at(self, distro):
        return distro.repository.pulp_last_updated

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_pulp(self, distro):
        repo = distro.repository
        remote = None
        if repo.remote:
            remote = ui_serializers.ContainerRemoteSerializer(
                repo.remote.cast(), context=self.context).data

        sign_state = repo.content.filter(
            pulp_type="container.signature"
        ).count() > 0 and "signed" or "unsigned"

        return {
            "repository": {
                "id": repo.pk,
                "pulp_type": repo.pulp_type,
                "version": repo.latest_version().number,
                "name": repo.name,
                "description": repo.description,
                "created_at": repo.pulp_created,
                "updated_at": repo.pulp_last_updated,
                "pulp_labels": repo.pulp_labels,
                "remote": remote,
                "sign_state": sign_state
            },
            "distribution": {
                "id": distro.pk,
                "name": distro.name,
                "created_at": distro.pulp_created,
                "updated_at": distro.pulp_last_updated,
                "base_path": distro.base_path,
                "pulp_labels": distro.pulp_labels,
            },
        }


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
    id = serializers.UUIDField(source='pk')
    pulp_href = IdentityField(view_name='content-container/tags-detail')
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    tagged_manifest = ManifestListSerializer()

    class Meta:
        model = container_models.Tag
        fields = (
            'id',
            'pulp_href',
            "name",
            "created_at",
            "updated_at",
            "tagged_manifest"
        )


class ContainerManifestSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source='pulp_id')
    config_blob = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    layers = serializers.SerializerMethodField()
    image_manifests = ManifestListManifestSerializer(many=True)
    pulp_href = IdentityField(view_name='content-container/manifests-detail')
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)

    class Meta:
        model = container_models.Manifest
        fields = (
            "id",
            "pulp_href",
            "digest",
            "schema_version",
            "media_type",
            "config_blob",
            "tags",
            "created_at",
            "updated_at",
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
    id = serializers.UUIDField(source='pulp_id')
    added = serializers.SerializerMethodField()
    removed = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)

    class Meta:
        model = core_models.RepositoryVersion
        fields = ("id", "added", "removed", "number", "created_at", "updated_at")

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
    created_at = serializers.DateTimeField(source='created', required=False, read_only=True)
    updated_at = serializers.DateTimeField(source='updated', required=False)

    class Meta:
        model = models.ContainerDistroReadme
        fields = (
            "updated_at",
            "created_at",
            "text"
        )

        read_only_fields = (
            "updated_at",
            "created_at"
        )
