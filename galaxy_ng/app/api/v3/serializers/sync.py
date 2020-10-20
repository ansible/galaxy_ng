from rest_framework import serializers

from pulp_ansible.app import viewsets as pulp_viewsets
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    CollectionRemote,
)

from galaxy_ng.app.constants import COMMUNITY_DOMAINS
from galaxy_ng.app.models.collectionsync import CollectionSyncTask


class AnsibleDistributionSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')

    class Meta:
        model = AnsibleDistribution
        fields = (
            'name',
            'base_path',
            'content_guard',
            'created_at',
            'updated_at',
        )


class LastSyncTaskMixin:

    def get_last_sync_task_queryset(self, obj):
        raise NotImplementedError("subclass must implement get_last_sync_task_queryset")

    def get_last_sync_task(self, obj):
        sync_task = self.get_last_sync_task_queryset(obj)
        if not sync_task:
            # UI handles `null` as "no status"
            return

        return {
            "task_id": sync_task.id,
            "state": sync_task.task.state,
            "started_at": sync_task.task.started_at,
            "finished_at": sync_task.task.finished_at,
            "error": sync_task.task.error
        }


class AnsibleRepositorySerializer(LastSyncTaskMixin, serializers.ModelSerializer):
    distributions = serializers.SerializerMethodField()
    last_sync_task = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')

    class Meta:
        model = AnsibleRepository
        fields = (
            'name',
            'description',
            'next_version',
            'distributions',
            'created_at',
            'updated_at',
            'last_sync_task',
        )

    def get_distributions(self, obj):
        return [
            AnsibleDistributionSerializer(distro).data
            for distro in obj.ansible_ansibledistribution.all()
        ]

    def get_last_sync_task_queryset(self, obj):
        return CollectionSyncTask.objects.filter(repository=obj).last()


class CollectionRemoteSerializer(LastSyncTaskMixin, pulp_viewsets.CollectionRemoteSerializer):
    last_sync_task = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    token = serializers.CharField(allow_null=True, required=False, max_length=2000, write_only=True)
    name = serializers.CharField(read_only=True)
    repositories = serializers.SerializerMethodField()

    class Meta:
        model = CollectionRemote
        fields = (
            'pk',
            'name',
            'url',
            'auth_url',
            'token',
            'policy',
            'requirements_file',
            'created_at',
            'updated_at',
            'username',
            'password',
            'proxy_url',
            'tls_validation',
            'client_key',
            'client_cert',
            'ca_cert',
            'last_sync_task',
            'repositories',
            'pulp_href',
            'download_concurrency',
        )
        extra_kwargs = {
            'name': {'read_only': True},
            'pulp_href': {'read_only': True},
            'password': {'write_only': True},
            'token': {'write_only': True},
            'client_key': {'write_only': True},
            'client_cert': {'write_only': True},
            'ca_cert': {'write_only': True},
        }

    def validate(self, data):
        if not data.get('requirements_file') and any(
            [domain in data['url'] for domain in COMMUNITY_DOMAINS]
        ):
            raise serializers.ValidationError(
                detail={
                    'requirements_file':
                        'Syncing content from community domains without specifying a '
                        'requirements file is not allowed.'
                }
            )
        return super().validate(data)

    def get_repositories(self, obj):
        return [
            AnsibleRepositorySerializer(repo).data
            for repo in obj.repository_set.all()
        ]

    def get_last_sync_task_queryset(self, obj):
        """Gets last_sync_task from Pulp using remote->repository relation"""

        return CollectionSyncTask.objects.filter(
            repository=obj.repository_set.order_by('-pulp_last_updated').first()
        ).first()
