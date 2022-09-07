import logging

from django.conf import settings

from drf_spectacular.utils import extend_schema

from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework.settings import perform_import

from galaxy_ng.app.api.v1.tasks import (
    legacy_sync_from_upstream
)

from galaxy_ng.app.api.v1.viewsets.tasks import LegacyTasksMixin
from galaxy_ng.app.api.v1.serializers import LegacySyncSerializer
from galaxy_ng.app.api.v1.serializers import LegacySyncTaskResponseSerializer
from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)


logger = logging.getLogger(__name__)


class LegacyRolesSyncViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin, LegacyTasksMixin):
    """Load roles from an upstream v1 source."""

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    serializer_class = LegacySyncSerializer

    @extend_schema(
        parameters=[],
        request=LegacySyncSerializer(),
        responses=LegacySyncTaskResponseSerializer()
    )
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kwargs = dict(serializer.validated_data)
        logger.debug(f'REQUEST kwargs: {kwargs}')
        task_id = self.legacy_dispatch(legacy_sync_from_upstream, kwargs=kwargs)
        return Response({'task': task_id})
