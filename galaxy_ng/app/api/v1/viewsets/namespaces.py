import logging

from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend

from drf_spectacular.utils import extend_schema_field

from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy

from galaxy_ng.app.api.v1.models import (
    LegacyNamespace,
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyNamespacesSerializer,
    LegacyUserSerializer
)

from galaxy_ng.app.api.v1.filtersets import LegacyNamespaceFilter
from galaxy_ng.app.api.v1.filtersets import LegacyUserFilter

from rest_framework.settings import perform_import


GALAXY_AUTHENTICATION_CLASSES = perform_import(
    settings.GALAXY_AUTHENTICATION_CLASSES,
    'GALAXY_AUTHENTICATION_CLASSES'
)

logger = logging.getLogger(__name__)


class LegacyNamespacesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyNamespacesViewSet(viewsets.ModelViewSet):
    """
    A list of legacy namespaces.

    The community UI has a view to list all legacy users.
    Each user is clickable and brings the browser to a
    page with a list of roles created by the user.

    Rather than make a hacky unmaintable viewset that
    aggregates usernames from the roles, this viewset
    goes directly to the legacy namespace/user table.

    We do not want to create this view from v3 namespaces
    because many/most legacy namespaces do not conform
    to the v3 namespace character requirements.

    TODO: allow edits of the avatar url
    TODO: allow edits of the "owners"
    TODO: allow mapping to a real namespace
    """

    queryset = LegacyNamespace.objects.all()
    pagination_class = LegacyNamespacesSetPagination
    serializer = LegacyNamespacesSerializer
    serializer_class = LegacyNamespacesSerializer

    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyNamespaceFilter

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @extend_schema_field(LegacyNamespacesSerializer)
    def retrieve(self, request, pk=None):
        """Get a single namespace."""
        user = LegacyNamespace.objects.filter(id=pk).first()
        serializer = LegacyNamespacesSerializer(user)
        return Response(serializer.data)


class LegacyUsersViewSet(viewsets.ModelViewSet):
    """
    A list of legacy users.

    The community UI has a view to list all legacy users.
    Each user is clickable and brings the browser to a
    page with a list of roles created by the user.

    Rather than make a hacky unmaintable viewset that
    aggregates usernames from the roles, this viewset
    goes directly to the legacy namespace/user table.

    We do not want to create this view from v3 namespaces
    because many/most legacy namespaces do not conform
    to the v3 namespace character requirements.

    TODO: allow edits of the avatar url
    TODO: allow edits of the "owners"
    TODO: allow mapping to a real namespace
    """

    queryset = LegacyNamespace.objects.all()
    pagination_class = LegacyNamespacesSetPagination
    serializer = LegacyUserSerializer
    serializer_class = LegacyUserSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyUserFilter

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @extend_schema_field(LegacyUserSerializer)
    def retrieve(self, request, pk=None):
        """Get a single user."""
        user = LegacyNamespace.objects.filter(id=pk).first()
        serializer = LegacyUserSerializer(user)
        return Response(serializer.data)
