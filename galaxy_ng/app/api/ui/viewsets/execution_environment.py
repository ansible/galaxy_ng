import logging

from django.db.models import Prefetch

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


class ManifestFilter(filterset.FilterSet):
    # tag = filters.CharFilter(method='tag_filter')
    sort = filters.OrderingFilter(
        fields=(
            ('pulp_created', 'created'),
        ),
    )

    class Meta:
        model = container_models.Manifest
        fields = {
            'digest': ['exact', 'icontains', 'contains', 'startswith'],
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
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ManifestFilter

    def get_queryset(self):
        base_path = self.kwargs["base_path"]
        repo = get_object_or_404(models.ContainerDistribution, base_path=base_path).repository
        repo_version = repo.latest_version()
        repo_content = repo_version.content.all()

        manifests = container_models.Manifest.objects\
            .filter(pk__in=repo_content)\
            .prefetch_related(
                # Prefetch limits the tag list to tags in the current repo version.
                # Without it, tags from all repo versions are allowed which leads
                # to duplicates.
                Prefetch(
                    'tagged_manifests',
                    container_models.Tag.objects.filter(pk__in=repo_content)),
                Prefetch(
                    'blobs',
                    container_models.Blob.objects.prefetch_related(
                        Prefetch('_artifacts', to_attr='artifact_list')),
                    to_attr='blob_list'),
                'config_blob'
            )

        # I know that this should go in the FilterSet, but I cannot for the life
        # of me figure out how to access base_path in the filterset. Without
        # base_path, it's impossible to filter the tags down to a specific repo version,
        # which means this query would end up pulling all of the tags in all repos
        # that match the tag param, which could potentially be thousands of objects.
        tag_filter = self.request.GET.get('tag', None)
        if tag_filter:
            manifests = manifests.filter(
                tagged_manifests__name__contains=tag_filter,
                # tagged_manifests doesn't respect the Prefetch filtering, so
                # the repo version has to be filtered again here
                tagged_manifests__pk__in=repo_content)

        return manifests
