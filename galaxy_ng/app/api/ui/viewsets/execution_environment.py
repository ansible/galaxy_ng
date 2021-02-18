import logging

from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers
from django.shortcuts import get_object_or_404
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app import models

log = logging.getLogger(__name__)


class RepositoryFilter(filterset.FilterSet):
    sort = filters.OrderingFilter(
        fields=(
            ('pulp_created', 'created'),
            ('name', 'name'),
            ('description', 'description'),
            ('repository__pulp_created', 'updated'),
        ),
    )

    class Meta:
        model = models.ContainerDistribution
        fields = {
            'name': ['exact', 'icontains', 'contains', 'startswith'],
            'description': ['exact', 'icontains', 'contains', 'startswith'],
        }


class ContainerRepositoryViewSet(api_base.ModelViewSet):
    queryset = models.ContainerDistribution.objects.all()
    serializer_class = serializers.ContainerRepositorySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RepositoryFilter
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]

    def get_object(self):
        base_path = self.kwargs["name"]
        if self.kwargs.get("namespace"):
            base_path = "{}/{}".format(self.kwargs["namespace"], self.kwargs["name"])

        return get_object_or_404(self.queryset, base_path=base_path)
