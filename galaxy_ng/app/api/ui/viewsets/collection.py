import galaxy_pulp
from django.conf import settings
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend, OrderingFilter
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action as drf_action
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from galaxy_ng.app import models
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.common import pulp
from galaxy_ng.app import constants


class CollectionViewSet(api_base.ViewSet):
    lookup_url_kwarg = 'collection'
    lookup_value_regex = r'[0-9a-z_]+/[0-9a-z_]+'

    def list(self, request, *args, **kwargs):
        self.paginator.init_from_request(request)

        params = {
            'offset': self.paginator.offset,
            'limit': self.paginator.limit,
        }
        for key, value in self.request.query_params.lists():
            if key == 'keywords':
                key = 'q'
            if isinstance(value, list):
                params[key] = ','.join(value)
            else:
                params[key] = value

        api = galaxy_pulp.PulpCollectionsApi(pulp.get_client())

        response = api.list(
            is_highest=True,
            exclude_fields='docs_blob',
            **params
        )

        namespaces = set(collection['namespace'] for collection in response.results)
        namespaces = self._query_namespaces(namespaces)

        data = serializers.CollectionListSerializer(
            response.results, many=True,
            context={'namespaces': namespaces}
        ).data
        return self.paginator.paginate_proxy_response(data, response.count)

    def retrieve(self, request, *args, **kwargs):
        namespace, name = self.kwargs['collection'].split('/')
        namespace_obj = get_object_or_404(models.Namespace, name=namespace)

        params_dict = self.request.query_params.dict()

        version = params_dict.get('version', '')

        api = galaxy_pulp.PulpCollectionsApi(pulp.get_client())

        params = {
            'namespace': namespace,
            'name': name,
        }

        if version == '':
            params['is_highest'] = True
            params['certification'] = constants.CertificationStatus.CERTIFIED.value
        else:
            params['version'] = version

        response = api.list(**params)

        if not response.results:
            raise NotFound()

        all_versions = api.list(
            namespace=namespace,
            name=name,
            fields='version,id,pulp_created,artifact',
            certification=constants.CertificationStatus.CERTIFIED.value
        )

        all_versions = [
            {
                'version': collection['version'],
                'id': collection['id'],
                'created': collection['pulp_created']
            } for collection in all_versions.results
        ]

        collection = response.results[0]

        data = serializers.CollectionDetailSerializer(
            collection,
            context={'namespace': namespace_obj, 'all_versions': all_versions}
        ).data

        return Response(data)

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, '_paginator'):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    @staticmethod
    def _query_namespaces(names):
        queryset = models.Namespace.objects.filter(name__in=names)
        namespaces = {ns.name: ns for ns in queryset}
        return namespaces


class CollectionVersionViewSet(api_base.GenericViewSet):
    lookup_url_kwarg = 'version'
    lookup_value_regex = r'[0-9a-z_]+/[0-9a-z_]+/[0-9A-Za-z.+-]+'
    serializer_class = serializers.CollectionVersionSerializer

    def list(self, request, *args, **kwargs):
        self.paginator.init_from_request(request)

        params = self.request.query_params.dict()
        params.update({
            'offset': self.paginator.offset,
            'limit': self.paginator.limit,
        })

        # pulp uses ordering, but the UI is standardized around sort
        if params.get('sort'):
            params['ordering'] = params.get('sort')
            del params['sort']

        api = galaxy_pulp.PulpCollectionsApi(pulp.get_client())
        response = api.list(exclude_fields='docs_blob', **params)

        data = serializers.CollectionVersionSerializer(response.results, many=True).data
        return self.paginator.paginate_proxy_response(data, response.count)

    @swagger_auto_schema(operation_summary="Retrieve collection version",
                         responses={200: serializers.CollectionVersionDetailSerializer})
    def retrieve(self, request, *args, **kwargs):
        namespace, name, version = self.kwargs['version'].split('/')

        api = galaxy_pulp.PulpCollectionsApi(pulp.get_client())
        response = api.list(namespace=namespace, name=name, version=version, limit=1)

        if not response.results:
            raise NotFound()

        data = serializers.CollectionVersionDetailSerializer(response.results[0]).data
        return Response(data)

    @drf_action(
        methods=["PUT"],
        detail=True,
        url_path="certified",
        permission_classes=api_base.GALAXY_PERMISSION_CLASSES + [
            permissions.IsPartnerEngineer
        ],
        serializer_class=serializers.CertificationSerializer
    )
    def set_certified(self, request, *args, **kwargs):
        namespace, name, version = self.kwargs['version'].split('/')
        namespace_obj = get_object_or_404(models.Namespace, name=namespace)
        self.check_object_permissions(request, namespace_obj)

        api = galaxy_pulp.GalaxyCollectionVersionsApi(pulp.get_client())
        serializer = serializers.CertificationSerializer(
            data=request.data,
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        certification = serializer.validated_data.get('certification')

        response = api.set_certified(
            prefix=settings.X_PULP_API_PREFIX,
            namespace=namespace,
            name=name,
            version=version,
            certification_info=galaxy_pulp.CertificationInfo(certification),
        )
        return Response(response)


class CollectionImportFilter(filterset.FilterSet):
    namespace = filters.CharFilter(field_name='namespace__name')
    created = filters.DateFilter(field_name='created_at')

    sort = OrderingFilter(
        fields=(('created_at', 'created'),)
    )

    class Meta:
        model = models.CollectionImport
        fields = ['namespace', 'name', 'version']


class CollectionImportViewSet(api_base.GenericViewSet):
    lookup_field = 'task_id'
    queryset = models.CollectionImport.objects.all()
    serializer_class = serializers.ImportTaskListSerializer

    filter_backends = [DjangoFilterBackend]
    filterset_class = CollectionImportFilter

    ordering_fields = ('created',)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        api = galaxy_pulp.GalaxyImportsApi(pulp.get_client())

        results = []
        for task in page:
            task_info = api.get(prefix=settings.X_PULP_API_PREFIX, id=str(task.pk))
            data = serializers.ImportTaskListSerializer(task_info, context={'task_obj': task}).data
            results.append(data)
        return self.get_paginated_response(results)

    @swagger_auto_schema(operation_summary="Retrieve collection import",
                         responses={200: serializers.ImportTaskDetailSerializer})
    def retrieve(self, request, *args, **kwargs):
        api = galaxy_pulp.GalaxyImportsApi(pulp.get_client())
        task = self.get_object()
        task_info = api.get(prefix=settings.X_PULP_API_PREFIX, id=self.kwargs['task_id'])
        data = serializers.ImportTaskDetailSerializer(task_info, context={'task_obj': task}).data
        return Response(data)
