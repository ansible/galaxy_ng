import logging

from galaxy_ng.app.api.v3.viewsets.namespace import NamespaceViewSet
from galaxy_ng.app.api.ui import serializers

log = logging.getLogger(__name__)


class NamespaceViewSet(NamespaceViewSet):
    serializer_class = serializers.NamespaceSerializer

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.NamespaceSummarySerializer
        elif self.action == 'update':
            return serializers.NamespaceUpdateSerializer
        else:
            return self.serializer_class
