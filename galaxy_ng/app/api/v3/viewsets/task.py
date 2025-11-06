import logging

from rest_framework import viewsets as drf_viewsets  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
from pulpcore.plugin.models import Task  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]

from galaxy_ng.app.api.base import LocalSettingsMixin
from galaxy_ng.app.api.v3.serializers import TaskSerializer, TaskSummarySerializer
from galaxy_ng.app.access_control import access_policy

log = logging.getLogger(__name__)


class TaskViewSet(LocalSettingsMixin, drf_viewsets.ReadOnlyModelViewSet):
    permission_classes = [access_policy.TaskAccessPolicy]
    serializer_class = TaskSerializer
    lookup_field = "pk"

    def get_queryset(self):
        # Order newest first and include related objects used by the serializer
        return (
            Task.objects.all()
            .select_related("worker")
            .prefetch_related("progress_reports")
            .order_by("-pulp_created")
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskSummarySerializer
        else:
            return self.serializer_class
