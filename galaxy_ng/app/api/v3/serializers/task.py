import logging
from rest_framework import serializers
from rest_framework.reverse import reverse
from pulpcore.app.serializers import ProgressReportSerializer
from pulpcore.plugin.models import Task


log = logging.getLogger(__name__)


class TaskSerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(source='pulp_created')
    updated_at = serializers.DateTimeField(source='pulp_last_updated')
    progress_reports = ProgressReportSerializer(many=True, read_only=True)
    pulp_id = serializers.UUIDField(source='pk')
    name = serializers.CharField()
    state = serializers.CharField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()

    class Meta:
        model = Task
        ref_name = "Task"
        fields = (
            'pulp_id',
            'name',
            'created_at',
            'updated_at',
            'finished_at',
            'started_at',
            'state',
            'error',
            'parent_task',
            'child_tasks',
            'progress_reports',
        )


class TaskSummarySerializer(TaskSerializer):
    """TaskSerializer but without detail fields.

    For use in /tasks/<str:pk>/ detail views."""
    href = serializers.SerializerMethodField()

    def get_href(self, obj) -> str:
        return reverse(
            'galaxy:api:v3:tasks-detail',
            kwargs={"pk": str(obj.pk)}
        )

    class Meta:
        model = Task
        fields = (
            'pulp_id',
            'name',
            'state',
            'started_at',
            'finished_at',
            'href',
        )
