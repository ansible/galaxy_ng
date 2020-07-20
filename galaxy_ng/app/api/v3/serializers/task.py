import logging

from rest_framework import serializers

from galaxy_ng.app.api.ui.serializers.base import Serializer

log = logging.getLogger(__name__)


class TaskSerializer(Serializer):
    pulp_id = serializers.UUIDField(source='pk')
    name = serializers.CharField()
    state = serializers.CharField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
