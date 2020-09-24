from typing import Any, Dict
from rest_framework import serializers
from pulpcore.plugin.models import Task
from pulp_ansible.app.models import CollectionRemote
from pulp_ansible.app.viewsets import CollectionRemoteSerializer
from galaxy_ng.app.models import CollectionSyncTask
from galaxy_ng.app.constants import COMMUNITY_DOMAINS


class SyncConfigSerializer(CollectionRemoteSerializer):
    created_at = serializers.DateTimeField(source='pulp_created', required=False)
    updated_at = serializers.DateTimeField(source='pulp_last_updated', required=False)
    token = serializers.CharField(allow_null=True, required=False, max_length=2000, write_only=True)
    name = serializers.CharField(read_only=True)

    class Meta:
        model = CollectionRemote
        fields = (
            'name',
            'url',
            'auth_url',
            'token',
            'policy',
            'requirements_file',
            'created_at',
            'updated_at',
        )

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


class TaskSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')
    worker = serializers.SerializerMethodField()

    def get_worker(self, obj) -> Dict[str, Any]:
        return {
            'name': obj.worker.name,
            'missing': obj.worker.missing,
            'last_heartbeat': obj.worker.last_heartbeat,
        }

    class Meta:
        model = Task
        fields = (
            'pk',
            'created_at',
            'updated_at',
            'finished_at',
            'started_at',
            'state',
            'error',
            'worker',
            'parent_task',
            'child_tasks',
        )


# Recursively add self referenced serializer field
TaskSerializer._declared_fields['child_tasks'] = TaskSerializer(many=True, read_only=True)
TaskSerializer._declared_fields['parent_task'] = TaskSerializer(read_only=True)


class SyncTaskSerializer(serializers.ModelSerializer):
    task = TaskSerializer(read_only=True)
    repository = serializers.CharField(source='repository.name')

    class Meta:
        fields = (
            'task',
            'repository',
        )
        model = CollectionSyncTask
