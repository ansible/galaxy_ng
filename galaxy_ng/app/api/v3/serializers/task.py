import logging
from typing import Any, Dict, Optional
from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from pulpcore.app.serializers import ProgressReportSerializer
from pulpcore.plugin.models import Task
from galaxy_ng.app.models import CollectionSyncTask


log = logging.getLogger(__name__)


class BaseTaskSerializer(serializers.ModelSerializer):
    pulp_id = serializers.UUIDField(source='pk')
    name = serializers.CharField()
    state = serializers.CharField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()


class TaskDetailSerializer(BaseTaskSerializer):
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')
    worker = serializers.SerializerMethodField()
    repository = serializers.SerializerMethodField()
    progress_reports = ProgressReportSerializer(many=True, read_only=True)

    @extend_schema_field(Optional[Dict[str, Any]])
    def get_worker(self, obj):
        if obj.worker:
            return {
                'name': obj.worker.name,
                'missing': obj.worker.missing,
                'last_heartbeat': obj.worker.last_heartbeat,
            }

    @extend_schema_field(Optional[str])
    def get_repository(self, obj):
        sync_task = CollectionSyncTask.objects.filter(task=obj).first()
        if sync_task:
            return sync_task.repository.name

    class Meta:
        model = Task
        fields = (
            'pulp_id',
            'name',
            'created_at',
            'updated_at',
            'finished_at',
            'started_at',
            'state',
            'error',
            'worker',
            'parent_task',
            'child_tasks',
            'repository',
            'progress_reports',
        )


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'pulp_id',
            'name',
            'state',
            'started_at',
            'finished_at',
        )
