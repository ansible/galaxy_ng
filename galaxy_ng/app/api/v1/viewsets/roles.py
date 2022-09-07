import logging

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema_field

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.settings import perform_import
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy

from galaxy_ng.app.api.v1.tasks import (
    legacy_role_import,
)
from galaxy_ng.app.api.v1.models import (
    LegacyRole
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyImportSerializer,
    LegacyRoleSerializer,
    LegacyRoleContentSerializer,
    LegacyRoleVersionsSerializer,
)

from galaxy_ng.app.api.v1.viewsets.tasks import LegacyTasksMixin
from galaxy_ng.app.api.v1.filtersets import LegacyRoleFilter


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)

logger = logging.getLogger(__name__)


class LegacyRolesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyRolesViewSet(viewsets.ModelViewSet):
    """A list of legacy roles."""

    queryset = LegacyRole.objects.all().order_by('full_metadata__created')
    ordering_fields = ('full_metadata__created')
    ordering = ('full_metadata__created')
    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyRoleFilter

    serializer_class = LegacyRoleSerializer
    pagination_class = LegacyRolesSetPagination

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    def destroy(self, request, pk=None):
        """Delete a single role."""
        role = LegacyRole.objects.filter(id=pk).first()
        role.delete()
        return Response({'status': 'ok'}, status=204)


class LegacyRoleContentViewSet(viewsets.GenericViewSet):
    """Documentation for a single legacy role."""

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @extend_schema_field(LegacyRoleContentSerializer)
    def retrieve(self, request, pk=None):
        """Get content for a single role."""
        role = LegacyRole.objects.filter(id=pk).first()
        serializer = LegacyRoleContentSerializer(role)
        return Response(serializer.data)


class LegacyRoleVersionsViewSet(viewsets.GenericViewSet):
    """A list of versions for a single legacy role."""

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @extend_schema_field(LegacyRoleVersionsSerializer)
    def retrieve(self, request, pk=None):
        """Get versions for a single role."""
        role = LegacyRole.objects.filter(id=pk).first()
        versions = role.full_metadata.get('versions', [])
        transformed = LegacyRoleVersionsSerializer(versions)
        paginated = {
            'count': len(transformed.data),
            'next': None,
            'next_link': None,
            'previous': None,
            'previous_link': None,
            'results': transformed.data[:]
        }
        return Response(paginated)


class LegacyRoleImportsViewSet(viewsets.GenericViewSet, LegacyTasksMixin):
    """Legacy role imports."""

    serializer_class = LegacyImportSerializer
    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kwargs = dict(serializer.validated_data)

        # tell the defered task who started this job
        kwargs['request_username'] = request.user.username

        # synthetically create the name for the response
        role_name = kwargs.get('alternate_role_name') or \
            kwargs['github_repo'].replace('ansible-role-', '')

        task_id = self.legacy_dispatch(legacy_role_import, kwargs=kwargs)

        return Response({
            'results': [{
                'id': task_id,
                'github_user': kwargs['github_user'],
                'github_repo': kwargs['github_repo'],
                'summary_fields': {
                    'role': {
                        'name': role_name
                    }
                }
            }]
        })
