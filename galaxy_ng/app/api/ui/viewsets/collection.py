from django.db.models import Exists, OuterRef, Q, Value, F, Func, CharField
from django.db.models import When, Case
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
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
    sign_state = filters.CharFilter(method="filter_by_sign_state")

    # The pulp core filtersets return a 400 on requests that include params that aren't
    # registered with a filterset. This is a hack to make the include_related fields work
    # on this viewset.
    include_related = filters.CharFilter(method="no_op")

    def filter_by_sign_state(self, qs, name, value):
        """Filter queryset qs by list of sign_state."""
        query_params = Q()
        for state in value.split(","):
            query_params |= Q(sign_state=state.strip())
        return qs.filter(query_params)

    def no_op(self, qs, name, value):
        return qs


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
        if getattr(self, "swagger_fake_view", False):
            # OpenAPI spec generation
            return CollectionVersion.objects.none()
        path = self.kwargs.get('distro_base_path')
        if path is None:
            raise Http404(_("Distribution base path is required"))

        base_versions_query = CollectionVersion.objects.filter(pk__in=self._distro_content)

        # Build a dict to be used by the annotation filter at the end of the method
        collection_versions = {}
        for collection_id, version in base_versions_query.values_list("collection_id", "version"):
            value = collection_versions.get(str(collection_id))
            if not value or semantic_version.Version(version) > semantic_version.Version(value):
                collection_versions[str(collection_id)] = version

        deprecated_query = AnsibleCollectionDeprecated.objects.filter(
            namespace=OuterRef("namespace"),
            name=OuterRef("name"),
            pk__in=self._distro_content,
        )

        if not collection_versions.items():
            return CollectionVersion.objects.none().annotate(
                # AAH-122: annotated filterable fields must exist in all the returned querysets
                #          in order for filters to work.
                deprecated=Exists(deprecated_query),
                sign_state=Value("unsigned"),
            )

        # The main queryset to be annotated
        version_qs = base_versions_query.select_related("collection")

        # AAH-1484 - replacing `Q(collection__id, version)` with this annotation
        # This builds `61505561-f806-4ddd-8f53-c403f0ec04ed:3.2.9` for each row.
        # this is done to be able to filter at the end of this method and
        # return collections only once and only for its highest version.
        version_identifier_expression = Func(
            F("collection__pk"), Value(":"), F("version"),
            function="concat",
            output_field=CharField(),
        )

        version_qs = version_qs.annotate(
            deprecated=Exists(deprecated_query),
            version_identifier=version_identifier_expression,
            sign_state=Case(
                When(signatures__isnull=False, then=Value("signed")),
                When(signatures__isnull=True, then=Value("unsigned")),
            )
        )

        # AAH-1484 - filtering by version_identifier
        version_qs = version_qs.filter(
            version_identifier__in=[
                ":".join([pk, version]) for pk, version in collection_versions.items()
            ]
        )

        return version_qs

    def get_object(self):
        """Return CollectionVersion object, latest or via query param 'version'."""
        version = self.request.query_params.get('version', None)
        if getattr(self, "swagger_fake_view", False):
            # OpenAPI spec generation
            return CollectionVersion.objects.none()

        if not version:
            queryset = self.get_queryset()
            return get_object_or_404(
                queryset, namespace=self.kwargs["namespace"], name=self.kwargs["name"]
            )

        base_qs = CollectionVersion.objects.filter(
            pk__in=self._distro_content,
            namespace=self.kwargs["namespace"],
            name=self.kwargs["name"],
        )
        return get_object_or_404(
            base_qs.annotate(
                sign_state=Case(
                    When(signatures__isnull=False, then=Value("signed")),
                    When(signatures__isnull=True, then=Value("unsigned")),
                )
            ),
            version=version,
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.CollectionListSerializer
        else:
            return serializers.CollectionDetailSerializer


class CollectionVersionFilter(filterset.FilterSet):
    dependency = filters.CharFilter(field_name="dependency", method="dependency_filter")
    repository = filters.CharFilter(field_name="repository", method="repo_filter")
    versioning_class = versioning.UIVersioning

    def dependency_filter(self, queryset, name, value):
        """Return all CollectionVersions that have a dependency on the Collection
        passed in the url string, ex: ?dependency=my_namespace.my_collection_name
        """
        return queryset.filter(dependencies__has_key=value)

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
        fields = {
            'name': ['exact', 'icontains', 'contains', 'startswith'],
            'namespace': ['exact', 'icontains', 'contains', 'startswith'],
            'version': ['exact', 'icontains', 'contains', 'startswith'],
        }


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

    @extend_schema(summary=_("Retrieve collection version"),
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
            raise NotFound(_('Collection version not found for: {}').format(self.kwargs["version"]))
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

    @extend_schema(summary=_("Retrieve collection import"),
                   responses={200: serializers.ImportTaskDetailSerializer})
    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        data = serializers.ImportTaskDetailSerializer(task).data
        return Response(data)


class CollectionRemoteViewSet(api_base.ModelViewSet):
    queryset = CollectionRemote.objects.all().order_by('name')
    serializer_class = CollectionRemoteSerializer

    permission_classes = [access_policy.CollectionRemoteAccessPolicy]
