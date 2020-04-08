from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend
from rest_framework import mixins

from galaxy_ng.app import models
from galaxy_ng.app.api import permissions
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers


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


class NamespaceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    api_base.GenericViewSet,
):
    lookup_field = "name"

    def get_permissions(self):
        permission_list = super().get_permissions()
        if self.request.method == 'POST':
            permission_list.append(permissions.IsPartnerEngineer())
        elif self.request.method == 'PUT':
            permission_list.append(permissions.IsNamespaceOwnerOrPartnerEngineer())
        return permission_list

    filter_backends = (DjangoFilterBackend,)

    filterset_class = NamespaceFilter

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.NamespaceSummarySerializer
        elif self.action == 'update':
            return serializers.NamespaceUpdateSerializer
        else:
            return serializers.NamespaceSerializer

    def get_queryset(self):
        return models.Namespace.objects.all()


class MyNamespaceViewSet(NamespaceViewSet):
    def get_queryset(self):
        # All namespaces for users in the partner-engineers groups

        if permissions.IsPartnerEngineer().has_permission(self.request, self):
            queryset = models.Namespace.objects.all()
            return queryset

        # Just the namespaces with groups the user is in
        queryset = models.Namespace.objects.filter(
            groups__in=self.request.user.groups.all())
        return queryset
