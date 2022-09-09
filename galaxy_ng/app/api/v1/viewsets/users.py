import logging

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema_field

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.serializers import (
    LegacyUserSerializer
)

from galaxy_ng.app.api.v1.filtersets import LegacyUserFilter

from rest_framework.settings import perform_import


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)

logger = logging.getLogger(__name__)


class LegacyUsersSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyUsersViewSet(viewsets.ModelViewSet):
    """
    A list of legacy users.

    The community UI has a view to list all legacy users.
    Each user is clickable and brings the browser to a
    page with a list of roles created by the user.
    """

    queryset = User.objects.all().order_by('id')
    pagination_class = LegacyUsersSetPagination
    serializer_class = LegacyUserSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyUserFilter

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @extend_schema_field(LegacyUserSerializer)
    def retrieve(self, request, pk=None):
        """Get a single user."""
        user = User.objects.filter(id=pk).first()
        serializer = LegacyUserSerializer(user)
        return Response(serializer.data)
