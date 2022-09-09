import logging

from django.db import transaction
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from drf_spectacular.utils import extend_schema

from rest_framework import viewsets
from rest_framework import mixins
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from galaxy_ng.app.access_control.access_policy import LegacyAccessPolicy

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.api.v1.models import (
    LegacyNamespace,
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyNamespacesSerializer,
    LegacyNamespaceOwnerSerializer,
    LegacyUserSerializer
)

from galaxy_ng.app.api.v1.filtersets import LegacyNamespaceFilter

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


class LegacyNamespacesViewSet(
    viewsets.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin
):
    """
    A list of legacy namespaces.

    The community UI has a view to list all legacy authors.
    Each author is clickable and brings the browser to a
    page with a list of roles created by the author.

    Rather than make a hacky unmaintable viewset that
    aggregates usernames from the roles, this viewset
    goes directly to the legacy namespace/user table.

    We do not want to create this view from v3 namespaces
    because many/most legacy namespaces do not conform
    to the v3 namespace character requirements.

    TODO: allow edits of the avatar url
    TODO: allow mapping to a real namespace
    """

    queryset = LegacyNamespace.objects.all().order_by('id')
    pagination_class = LegacyNamespacesSetPagination
    serializer_class = LegacyNamespacesSerializer

    filter_backends = (DjangoFilterBackend,)
    filterset_class = LegacyNamespaceFilter

    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    @transaction.atomic
    def destroy(self, request, pk=None):
        return super().destroy(self, request, pk)


class LegacyNamespaceOwnersViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):
    """
    LegacyNamespace owners.

    Each owner has the permissions to:
        * modify the namespace owners
        * delete the namespace and it's roles
        * import new roles and versions for the namespace
    """

    serializer_class = LegacyUserSerializer
    pagination_class = None
    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    def get_queryset(self):
        return get_object_or_404(LegacyNamespace, pk=self.kwargs["pk"]).owners.all()

    @extend_schema(
        parameters=[LegacyNamespaceOwnerSerializer(many=True)],
        request=LegacyNamespaceOwnerSerializer(many=True),
        responses=LegacyUserSerializer(many=True)
    )
    def update(self, request, pk):
        ns = get_object_or_404(LegacyNamespace, pk=pk)

        try:
            pks = [user['id'] for user in request.data.get('owners', [])]
        except KeyError:
            raise exceptions.ValidationError("id is required", code="invalid")

        new_owners = User.objects.filter(pk__in=pks)

        if len(pks) != new_owners.count():
            raise exceptions.ValidationError("user doesn't exist", code="invalid")

        ns.owners.set(new_owners)

        return Response(self.serializer_class(ns.owners.all(), many=True).data)
