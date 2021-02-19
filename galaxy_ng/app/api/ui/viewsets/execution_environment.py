import logging
from pulp_container.app import models as container_models

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
            ('repository__pulp_created', 'created'),
            ('name', 'name'),
            ('description', 'description'),
            ('repository__pulp_last_updated', 'updated'),
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
    lookup_field = "base_path"


class ContainerRepositoryManifestViewSet(api_base.ModelViewSet):
    serializer_class = serializers.ContainerRepositoryImageSerializer

    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]

    def get_queryset(self):
        base_path = self.kwargs["base_path"]
        repo = get_object_or_404(models.ContainerDistribution, base_path=base_path).repository
        repo_version = repo.latest_version()

        # set the repo version as an attribute of the viewset so it's available to
        # the serializer so that the serializer can limit tags to tags that are in
        # the current repo version
        self.repository_version = repo_version

        return container_models.Manifest.objects.filter(pk__in=repo_version.content.all())
