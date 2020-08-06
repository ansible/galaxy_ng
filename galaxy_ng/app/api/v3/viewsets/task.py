import logging

from pulpcore.plugin import viewsets as pulp_core_viewsets

from galaxy_ng.app.api.base import GALAXY_PERMISSION_CLASSES, LocalSettingsMixin
from galaxy_ng.app.api.v3.serializers import TaskSerializer


log = logging.getLogger(__name__)


class TaskViewSet(LocalSettingsMixin, pulp_core_viewsets.TaskViewSet):
    permission_classes = GALAXY_PERMISSION_CLASSES
    serializer_class = TaskSerializer
