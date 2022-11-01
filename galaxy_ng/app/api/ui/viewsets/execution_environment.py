import logging

from django_filters import filters
from django_filters.rest_framework import filterset
from pulp_container.app import models as container_models

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.api.utils import GetObjectByIdMixin

log = logging.getLogger(__name__)


class ContainerRegistryRemoteFilter(filterset.FilterSet):
    name = filters.CharFilter(field_name='name')
    url = filters.CharFilter(field_name='url')
    created_at = filters.CharFilter(field_name='pulp_created')
    updated_at = filters.CharFilter(field_name='pulp_last_updated')

    sort = filters.OrderingFilter(
        fields=(
            ('name', 'name'),
            ('url', 'url'),
            ('pulp_created', 'created_at'),
            ('pulp_last_updated', 'updated_at'),
        ),
    )

    class Meta:
        model = models.ContainerRegistryRemote
        fields = {
            'name': ['exact', 'icontains', 'contains', 'startswith'],
            'url': ['exact', 'icontains', 'contains', 'startswith'],
        }


class ContainerRegistryRemoteViewSet(GetObjectByIdMixin, api_base.ModelViewSet):
    queryset = models.ContainerRegistryRemote.objects.all()
    serializer_class = serializers.ContainerRegistryRemoteSerializer
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    filterset_class = ContainerRegistryRemoteFilter


class ContainerRemoteViewSet(GetObjectByIdMixin, api_base.ModelViewSet):
    queryset = container_models.ContainerRemote.objects.all()
    serializer_class = serializers.ContainerRemoteSerializer
    permission_classes = [access_policy.ContainerRemoteAccessPolicy]
