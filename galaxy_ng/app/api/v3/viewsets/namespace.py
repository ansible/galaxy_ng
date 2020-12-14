from django.db import transaction
from django.db.models import Q
from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from galaxy_ng.app import models
from galaxy_ng.app.access_control.access_policy import NamespaceAccessPolicy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3 import serializers
from galaxy_ng.app.exceptions import ConflictError


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
            queryset = queryset.filter(Q(name__icontains=keyword) | Q(company__icontains=keyword))

        return queryset


class NamespaceViewSet(api_base.ModelViewSet):
    lookup_field = "name"
    queryset = models.Namespace.objects.all()
    serializer_class = serializers.NamespaceSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = NamespaceFilter
    swagger_schema = None
    permission_classes = [NamespaceAccessPolicy]

    def get_serializer_class(self):
        if self.action == 'list':
            return serializers.NamespaceSummarySerializer
        else:
            return self.serializer_class

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Override to validate for name duplication before serializer validation."""
        name = request.data.get('name')
        if name and models.Namespace.objects.filter(name=name).exists():
            # Ensures error raised is 409, not 400.
            raise ConflictError(
                detail={'name': f'A namespace named {name} already exists.'}
            )
        return super().create(request, *args, **kwargs)
