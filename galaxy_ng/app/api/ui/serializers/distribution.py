from rest_framework import serializers
from pulp_ansible.app import models as pulp_models


class RepositorySerializer(serializers.ModelSerializer):
    content_count = serializers.SerializerMethodField()

    class Meta:
        model = pulp_models.AnsibleRepository
        fields = (
            'name',
            'description',
            'pulp_id',
            'pulp_last_updated',
            'content_count'
        )

    def get_content_count(self, repo):
        return repo.latest_version().content.count()


class DistributionSerializer(serializers.ModelSerializer):
    repository = RepositorySerializer()

    class Meta:
        model = pulp_models.AnsibleDistribution
        fields = (
            'pulp_id',
            'name',
            'base_path',
            'repository'
        )
