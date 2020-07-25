import logging

from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from galaxy_ng.app import models
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3 import serializers

log = logging.getLogger(__name__)


class NamespaceFilter(filterset.FilterSet):
    keywords = filters.CharFilter(method='keywords_filter')

    sort = filters.OrderingFilter(
        fields=(
            ('name', 'name'),
            ('company', 'company'),
            ('id', 'id'),
        ),
    )

    class Meta:
        model = models.Namespace
        fields = ('name', 'company',)

    def keywords_filter(self, queryset, name, value):

        keywords = self.request.query_params.getlist('keywords')

        for keyword in keywords:
            queryset = queryset.filter(name=keyword)

        return queryset


class NamespaceViewSet(api_base.ModelViewSet):
    lookup_field = "name"
    queryset = models.Namespace.objects.all()
    serializer_class = serializers.NamespaceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = NamespaceFilter
    swagger_schema = None

    def get_permissions(self):
        permission_list = super().get_permissions()
        if self.request and self.request.method == 'POST':
            permission_list.append(permissions.IsPartnerEngineer())
        elif self.request and self.request.method == 'PUT':
            permission_list.append(permissions.IsNamespaceOwnerOrPartnerEngineer())

        return permission_list
