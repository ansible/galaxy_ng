from django.core.exceptions import ObjectDoesNotExist
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend, OrderingFilter
from drf_spectacular.utils import extend_schema
from pulp_ansible.app.galaxy.v3 import views as pulp_ansible_galaxy_views
from pulp_ansible.app.viewsets import CollectionVersionFilter
from pulp_ansible.app.models import (
    AnsibleDistribution,
    CollectionVersion,
    Collection,
    CollectionRemote,
)
from pulp_ansible.app.models import CollectionImport as PulpCollectionImport
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers, versioning
from galaxy_ng.app.api.v3.serializers.sync import CollectionRemoteSerializer


class CollectionFilter(CollectionVersionFilter):
    versioning_class = versioning.UIVersioning
    keywords = filters.CharFilter(field_name="keywords", method="filter_by_q")


class CollectionViewSet(api_base.LocalSettingsMixin, pulp_ansible_galaxy_views.CollectionViewSet):
    """ Viewset that uses CollectionVersion to display data for Collection."""
    versioning_class = versioning.UIVersioning
    filterset_class = CollectionFilter
    permission_classes = [access_policy.CollectionAccessPolicy]

    # TODO(awcrosby): remove once pulp_ansible is_highest param filters by repo
    # https://pulp.plan.io/issues/7428
    def get_queryset(self):
        """
        Overrides to not use is_highest param and
        ensures one collection version per collection is returned.
        """
        distro_content = self.get_distro_content(self.kwargs["path"])

        # isolate the use of distinct in separate database call to avoid
        # postgres error on use of distinct and order_by in later calls
        qs_distinct = CollectionVersion.objects.filter(
            pk__in=distro_content).distinct('collection')
        collection_version_pks = [cv.pk for cv in qs_distinct]

        qs = CollectionVersion.objects.select_related("collection").filter(
            pk__in=collection_version_pks)
        return qs

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
