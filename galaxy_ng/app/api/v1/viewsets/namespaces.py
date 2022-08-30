import logging

from django.db.models import Q

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


logger = logging.getLogger(__name__)


class LegacyNamespacesSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class LegacyUsernameMixin:

    def get_queryset(self):

        logger.debug(f'QUERY_PARAMS: {self.request.query_params}')

        keywords = None
        if self.request.query_params.get('keywords'):
            keywords = self.request.query_params.get('keywords').rstrip('/')

        order_by = 'name'
        if self.request.query_params.get('order_by'):
            order_by = self.request.query_params.get('order_by').rstrip('/')

        if self.request.query_params.get('name'):
            print('BY NAME')
            name = self.request.query_params.get('name').rstrip('/')
            return LegacyNamespace.objects.filter(name=name).order_by(order_by)

        # users have a username, whereas namespaces have a name
        if self.request.query_params.get('username'):
            print('BY USERNAME')
            name = self.request.query_params.get('username').rstrip('/')
            return LegacyNamespace.objects.filter(name=name).order_by(order_by)

        if keywords:
            return LegacyNamespace.objects.filter(
                Q(name__contains=keywords)
            ).order_by(order_by)

        print('NO FILTERING')
        return LegacyNamespace.objects.all().order_by(order_by)


class LegacyNamespacesViewSet(LegacyUsernameMixin, viewsets.ModelViewSet):
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

    # queryset = LegacyNamespace.objects.all().order_by('name')
    serializer = LegacyNamespacesSerializer
    serializer_class = LegacyNamespacesSerializer
    # permission_classes = [AllowAny]
    permission_classes = [LegacyAccessPolicy]
    pagination_class = LegacyNamespacesSetPagination

    @extend_schema_field(LegacyNamespacesSerializer)
    def retrieve(self, request, pk=None):
        """Get a single namespace."""
        user = LegacyNamespace.objects.filter(id=pk).first()
        serializer = LegacyNamespacesSerializer(user)
        return Response(serializer.data)


class LegacyUsersViewSet(LegacyUsernameMixin, viewsets.ModelViewSet):
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

    # queryset = LegacyNamespace.objects.all().order_by('name')
    serializer = LegacyUserSerializer
    serializer_class = LegacyUserSerializer
    # permission_classes = [AllowAny]
    permission_classes = [LegacyAccessPolicy]
    pagination_class = LegacyNamespacesSetPagination

    @extend_schema_field(LegacyUserSerializer)
    def retrieve(self, request, pk=None):
        """Get a single user."""
        user = LegacyNamespace.objects.filter(id=pk).first()
        serializer = LegacyUserSerializer(user)
        return Response(serializer.data)
