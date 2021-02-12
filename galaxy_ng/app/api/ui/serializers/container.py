from rest_framework import serializers
from galaxy_ng.app import models
from galaxy_ng.app.access_control.fields import GroupPermissionField

from pulp_container.app import models as container_models


class ContainerDistributionSerializer(serializers.ModelSerializer):
    repository = serializers.SerializerMethodField()
    groups = GroupPermissionField()
    # namespace = serializers.SerializerMethodField()

    class Meta:
        model = models.ContainerDistribution
        fields = (
            'pulp_id',
            'name',
            'pulp_created',
            'base_path',
            'groups',
            'repository',
            # Missing namespace and description which are available in 2.3
            # 'namespace',
            # 'description',
        )

    def get_namespace(self, distro):
        return distro.namespace.name

    def get_repository(self, distro):
        repo = distro.repository

        return {
            'pulp_id': repo.pulp_id,
            'pulp_type': repo.pulp_type,
            'version': repo.latest_version().number,
            'name': repo.name,
            'description': repo.description,
            'pulp_created': repo.pulp_created
        }
