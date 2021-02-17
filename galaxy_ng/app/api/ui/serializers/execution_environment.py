from rest_framework import serializers
from pulp_container.app import models as container_models

from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import GroupPermissionField


class ContainerRepositorySerializer(serializers.ModelSerializer):
    pulp = serializers.SerializerMethodField()
    groups = GroupPermissionField()
    namespace = serializers.SerializerMethodField()
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
        fields = (
            'id',
            'name',
            'groups',

            # this field will return null on instances where hub is indexing a
            # different repo
            'pulp',
            'namespace',
            'description',
            'created',
            'updated'
        )

    def get_id(self, distro):
        return distro.pulp_id

    def get_created(self, distro):
        return distro.repository.pulp_created

    def get_updated(self, distro):
        return distro.repository.pulp_last_updated

    def get_namespace(self, distro):
        return distro.namespace.name

    def get_pulp(self, distro):
        repo = distro.repository

        return {
            'repository':
            {
                'pulp_id': repo.pulp_id,
                'pulp_type': repo.pulp_type,
                'version': repo.latest_version().number,
                'name': repo.name,
                'description': repo.description,
                'pulp_created': repo.pulp_created,
            },
            'distribution':
            {
                'pulp_id': distro.pulp_id,
                'name': distro.name,
                'pulp_created': distro.pulp_created,
                'base_path': distro.base_path,
            }
        }


class ContainerRepositoryImageSerializer(serializers.ModelSerializer):
    config_blob = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta:
        model = container_models.Manifest
        fields = (
            'pulp_id',
            'digest',
            'schema_version',
            'media_type',
            'config_blob',
            'tags',
            'pulp_created'
        )

    def get_config_blob(self, obj):
        return obj.config_blob.digest

    def get_tags(self, obj):
        tags = []

        # tagget_manifests returns all tags on the manifest, not just the ones
        # that are in the latest version of the repo.
        repo_content = self.context['view'].repository_version.content.all()
        tag_qs = obj.tagged_manifests.filter(pk__in=repo_content)

        for tag in tag_qs:
            tags.append(tag.name)

        return tags
