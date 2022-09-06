import logging

from django.conf import settings

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.settings import perform_import

from drf_spectacular.utils import extend_schema_field

from galaxy_ng.app.api.v1.tasks import (
    legacy_sync_from_upstream
)

from galaxy_ng.app.api.v1.viewsets.tasks import LegacyTasksMixin
from galaxy_ng.app.api.v1.serializers import LegacyTaskSerializer
from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)


logger = logging.getLogger(__name__)


class LegacyRolesSyncViewSet(viewsets.GenericViewSet, LegacyTasksMixin):
    """Load roles from an upstream v1 source."""

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @extend_schema_field(LegacyTaskSerializer)
    def create(self, request):
        """Create a new sync task."""
        kwargs = {
            'baseurl': request.data.get(
                'baseurl',
                'https://galaxy.ansible.com/api/v1/roles/'
            ),
            'github_user': request.data.get('github_user'),
            'role_name': request.data.get('role_name'),
            'role_version': request.data.get('role_name'),
            'limit': request.data.get('limit')
        }
        logger.debug(f'REQUEST DATA: {request.data}')
        logger.debug(f'REQUEST kwargs: {kwargs}')

        task_id = self.legacy_dispatch(legacy_sync_from_upstream, kwargs=kwargs)
        return Response({'task': task_id})
