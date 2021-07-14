from django.db.models import Exists, OuterRef, Q
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend, OrderingFilter
from drf_spectacular.utils import extend_schema
from pulp_ansible.app.galaxy.v3 import views as pulp_ansible_galaxy_views
from pulp_ansible.app import viewsets as pulp_ansible_viewsets
from pulp_ansible.app.models import (
    AnsibleCollectionDeprecated,
    AnsibleDistribution,
    CollectionVersion,
    Collection,
    CollectionRemote,
)
from pulp_ansible.app.models import CollectionImport as PulpCollectionImport
from rest_framework import mixins
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
import semantic_version

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers, versioning
from galaxy_ng.app.api.v3.serializers.sync import CollectionRemoteSerializer


class CollectionByCollectionVersionFilter(pulp_ansible_viewsets.CollectionVersionFilter):
    """pulp_ansible CollectionVersion filter for Collection viewset."""
    versioning_class = versioning.UIVersioning
    keywords = filters.CharFilter(field_name="keywords", method="filter_by_q")
    deprecated = filters.BooleanFilter()


class CollectionViewSet(
    api_base.GenericViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    pulp_ansible_galaxy_views.AnsibleDistributionMixin,
):
    """Viewset that uses CollectionVersion's within distribution to display data for Collection's.

    Collection list is filterable by FilterSet and includes latest CollectionVersion.

    Collection detail includes CollectionVersion that is latest or via query param 'version'.
    """
    versioning_class = versioning.UIVersioning
    filterset_class = CollectionByCollectionVersionFilter
    permission_classes = [access_policy.CollectionAccessPolicy]

    def get_queryset(self):
        """Returns a CollectionVersions queryset for specified distribution."""
        path = self.kwargs.get('path')
        if path is None:
            raise Http404("Distribution base path is required")

        distro_content = self.get_distro_content(path)
        repo_version = self.get_repository_version(path)

        versions = CollectionVersion.objects.filter(pk__in=distro_content).values_list(
            "collection_id",
            "version",
        )

        collection_versions = {}
        for collection_id, version in versions:
            value = collection_versions.get(str(collection_id))
            if not value or semantic_version.Version(version) > semantic_version.Version(value):
                collection_versions[str(collection_id)] = version

        if not collection_versions.items():
            return CollectionVersion.objects.none().annotate(
                # AAH-122: annotated fields must exist in all the returned querysets
                #          in order for filters to work.
                deprecated=Exists(AnsibleCollectionDeprecated.objects)
            )

        query_params = Q()
        for collection_id, version in collection_versions.items():
            query_params |= Q(collection_id=collection_id, version=version)

        deprecated_query = AnsibleCollectionDeprecated.objects.filter(
            collection=OuterRef("collection"), repository_version=repo_version
        )
        version_qs = CollectionVersion.objects.select_related("collection").filter(query_params)
        version_qs = version_qs.annotate(deprecated=Exists(deprecated_query))
        return version_qs

    def get_object(self):
        """Return CollectionVersion object, latest or via query param 'version'."""
        version = self.request.query_params.get('version', None)

        if not version:
            queryset = self.get_queryset()
            return get_object_or_404(
                queryset, namespace=self.kwargs["namespace"], name=self.kwargs["name"]
            )

        distro_content = self.get_distro_content(self.kwargs["path"])
        return get_object_or_404(
            CollectionVersion.objects.all(),
            pk__in=distro_content,
            namespace=self.kwargs["namespace"],
            name=self.kwargs["name"],
            version=version,
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CollectionListSerializer
        else:
            return serializers.CollectionDetailSerializer


# TODO: Remove when ui is updated and no longer uses this endpoint
class CollectionViewSetDeprecated(CollectionViewSet):
    """Temporary support of old /_ui/collections/ endpoint without use of
    certification flag. This shows content from the 'published' repo."""

    def get_queryset(self):
        self.kwargs["path"] = 'published'
        return super().get_queryset()


class CollectionVersionFilter(filterset.FilterSet):
    repository = filters.CharFilter(field_name='repository', method='repo_filter')
    versioning_class = versioning.UIVersioning

    def repo_filter(self, queryset, name, value):
        try:
            distro = AnsibleDistribution.objects.get(base_path=value)
            repository_version = distro.repository.latest_version()
            return queryset.filter(pk__in=repository_version.content)
        except ObjectDoesNotExist:
            return CollectionVersion.objects.none()

    sort = OrderingFilter(
        fields=(
            ('pulp_created', 'pulp_created'),
            ('namespace', 'namespace'),
            ('name', 'collection'),
            ('version', 'version'),
        )
    )

    class Meta:
        model = CollectionVersion
        fields = ['namespace', 'name', 'version', 'repository']


class CollectionVersionViewSet(api_base.GenericViewSet):
    lookup_url_kwarg = 'version'
    lookup_value_regex = r'[0-9a-z_]+/[0-9a-z_]+/[0-9A-Za-z.+-]+'
    queryset = CollectionVersion.objects.all()
    serializer_class = serializers.CollectionVersionSerializer
    filterset_class = CollectionVersionFilter
    versioning_class = versioning.UIVersioning

    permission_classes = [access_policy.CollectionAccessPolicy]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @extend_schema(summary="Retrieve collection version",
                   responses={200: serializers.CollectionVersionDetailSerializer})
    def retrieve(self, request, *args, **kwargs):
        namespace, name, version = self.kwargs['version'].split('/')
        try:
            collection_version = CollectionVersion.objects.get(
                namespace=namespace,
                collection=Collection.objects.get(namespace=namespace, name=name),
                version=version,
            )
        except ObjectDoesNotExist:
            raise NotFound(f'Collection version not found for: {self.kwargs["version"]}')
        serializer = serializers.CollectionVersionDetailSerializer(collection_version)
        return Response(serializer.data)


class CollectionImportFilter(filterset.FilterSet):
    namespace = filters.CharFilter(field_name='galaxy_import__namespace__name')
    name = filters.CharFilter(field_name='galaxy_import__name')
    keywords = filters.CharFilter(field_name='galaxy_import__name', lookup_expr='icontains')
    state = filters.CharFilter(field_name='task__state')
    version = filters.CharFilter(field_name='galaxy_import__version')
    created = filters.DateFilter(field_name='galaxy_import__created_at')
    versioning_class = versioning.UIVersioning

    sort = OrderingFilter(
        fields=(('galaxy_import__created_at', 'created'),)
    )

    class Meta:
        model = PulpCollectionImport
        fields = ['namespace',
                  'name',
                  'keywords',
                  'state',
                  'version']


class CollectionImportViewSet(api_base.GenericViewSet,
                              pulp_ansible_galaxy_views.CollectionImportViewSet):
    lookup_field = 'task_id'
    queryset = PulpCollectionImport.objects.prefetch_related("task", "galaxy_import").all()
    serializer_class = serializers.ImportTaskListSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = CollectionImportFilter

    versioning_class = versioning.UIVersioning

    ordering_fields = ('created',)

    permission_classes = [access_policy.CollectionAccessPolicy]

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.ImportTaskListSerializer
        else:
            return serializers.ImportTaskDetailSerializer

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page, many=True)

        return self.get_paginated_response(serializer.data)

    @extend_schema(summary="Retrieve collection import",
                   responses={200: serializers.ImportTaskDetailSerializer})
    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        data = serializers.ImportTaskDetailSerializer(task).data
        return Response(data)


class CollectionRemoteViewSet(api_base.ModelViewSet):
    queryset = CollectionRemote.objects.all().order_by('name')
    serializer_class = CollectionRemoteSerializer

    permission_classes = [access_policy.CollectionRemoteAccessPolicy]
