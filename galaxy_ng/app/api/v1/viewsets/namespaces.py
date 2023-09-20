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
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners
from galaxy_ng.app.utils.rbac import add_user_to_v3_namespace
from galaxy_ng.app.utils.rbac import remove_user_from_v3_namespace

from galaxy_ng.app.models.auth import User
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import (
    LegacyNamespace,
)
from galaxy_ng.app.api.v1.serializers import (
    LegacyNamespacesSerializer,
    LegacyNamespaceOwnerSerializer,
    LegacyNamespaceProviderSerializer,
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

    def create(self, request):

        ns_name = request.data.get('name')
        namespace, created = LegacyNamespace.objects.get_or_create(name=ns_name)

        return Response(
            self.serializer_class(
                namespace,
                many=False
            ).data
        )


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
        # return get_object_or_404(LegacyNamespace, pk=self.kwargs["pk"]).owners.all()
        ns = get_object_or_404(LegacyNamespace, pk=self.kwargs["pk"])
        if ns.namespace:
            return get_v3_namespace_owners(ns.namespace)
        return []

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

        # get the foreign key ...
        v3_namespace = ns.namespace

        # get the list of current owners
        current_owners = get_v3_namespace_owners(v3_namespace)

        # remove all owners not in the new list
        for current_owner in current_owners:
            if current_owner not in new_owners:
                remove_user_from_v3_namespace(current_owner, v3_namespace)

        # add new owners if not in the list
        for new_owner in new_owners:
            if new_owner not in current_owners:
                add_user_to_v3_namespace(new_owner, v3_namespace)

        return Response(
            self.serializer_class(
                get_v3_namespace_owners(v3_namespace),
                many=True
            ).data
        )


class LegacyNamespaceProvidersViewSet(viewsets.GenericViewSet, mixins.ListModelMixin):

    serializer_class = LegacyNamespaceProviderSerializer
    pagination_class = None
    permission_classes = [LegacyAccessPolicy]
    authentication_classes = GALAXY_AUTHENTICATION_CLASSES

    def get_queryset(self):
        ns = get_object_or_404(LegacyNamespace, pk=self.kwargs["pk"])
        if ns.namespace:
            return [ns.namespace]
        return []

    def update(self, request, pk):
        '''Bind a v3 namespace to the legacy namespace'''
        legacy_ns = get_object_or_404(LegacyNamespace, pk=pk)

        v3_id = request.data['id']
        v3_namespace = get_object_or_404(Namespace, id=v3_id)

        if legacy_ns.namespace != v3_namespace:
            legacy_ns.namespace = v3_namespace
            legacy_ns.save()

        return Response({})
