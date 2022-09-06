import logging

from django.conf import settings
from django.http import HttpResponse
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
    LegacyRoleSerializer,
    LegacyRoleContentSerializer,
    LegacyRoleVersionsSerializer,
)

from galaxy_ng.app.api.v1.viewsets.tasks import LegacyTasksViewset
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


class LegacyRoleBaseViewSet(viewsets.ModelViewSet, LegacyTasksViewset):
    """Base class for legacy roles."""

    queryset = LegacyRole.objects.all().order_by('full_metadata__created')
    ordering_fields = ('full_metadata__created')
    ordering = ('full_metadata__created')
    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyRoleFilter

    serializer = LegacyRoleSerializer
    serializer_class = LegacyRoleSerializer
    pagination_class = LegacyRolesSetPagination

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES


class LegacyRolesViewSet(LegacyRoleBaseViewSet):
    """A list of legacy roles."""


class LegacyRoleImportsViewSet(LegacyRoleBaseViewSet):
    """Legacy role imports."""

    def _validate_create_kwargs(self, kwargs):
        try:
            assert kwargs.get('github_user') is not None
            assert kwargs.get('github_user') != ''
            assert kwargs.get('github_repo') is not None
            assert kwargs.get('github_repo') != ''
            if kwargs.get('alternate_role_name'):
                assert kwargs.get('alternate_role_name') != ''
        except Exception as e:
            return e

    def create(self, request):
        """Import a new role or new role version."""
        data = request.data

        kwargs = {
            'request_username': request.user.username,
            'github_user': data.get('github_user'),
            'github_repo': data.get('github_repo'),
            'github_reference': data.get('github_reference'),
            'alternate_role_name': data.get('alternate_role_name'),
        }
        error = self._validate_create_kwargs(kwargs)
        if error:
            return HttpResponse(str(error), status=403)

        task_id = self.legacy_dispatch(legacy_role_import, kwargs=kwargs)

        role_name = kwargs['alternate_role_name'] or \
            kwargs['github_repo'].replace('ansible-role-', '')

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


class LegacyRoleViewSet(LegacyRoleBaseViewSet):
    """A single legacy role."""

    def get_object(self):
        """Helper function for access policy"""
        id = self.kwargs['id']
        return LegacyRole.objects.filter(id=id).first()

    @extend_schema_field(LegacyRoleSerializer)
    def retrieve(self, request, id=None):
        """Get a single role."""
        role = LegacyRole.objects.filter(id=id).first()
        serializer = LegacyRoleSerializer(role)
        return Response(serializer.data)

    def destroy(self, request, id=None):
        """Delete a single role."""
        role = LegacyRole.objects.filter(id=id).first()
        role.delete()
        return Response({'status': 'ok'})


class LegacyRoleContentViewSet(LegacyRoleBaseViewSet):
    """Documentation for a single legacy role."""

    @extend_schema_field(LegacyRoleContentSerializer)
    def retrieve(self, request, id=None):
        """Get content for a single role."""
        role = LegacyRole.objects.filter(id=id).first()
        serializer = LegacyRoleContentSerializer(role)
        return Response(serializer.data)


class LegacyRoleVersionsViewSet(LegacyRoleBaseViewSet):
    """A list of versions for a single legacy role."""

    @extend_schema_field(LegacyRoleVersionsSerializer)
    def retrieve(self, request, id=None):
        """Get versions for a single role."""
        role = LegacyRole.objects.filter(id=id).first()
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
