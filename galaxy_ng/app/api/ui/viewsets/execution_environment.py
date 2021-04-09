import logging

from django.db.models import Prefetch, Count, Q
from django.core import exceptions

from pulpcore.plugin import models as core_models
from pulp_container.app import models as container_models

from django_filters import filters
from django_filters.rest_framework import filterset, DjangoFilterBackend

from guardian.shortcuts import get_objects_for_user

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers
from django.shortcuts import get_object_or_404
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app import models

log = logging.getLogger(__name__)


class RepositoryFilter(filterset.FilterSet):
    my_permissions = filters.CharFilter(method='has_permissions')

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

    def has_permissions(self, queryset, name, value):
        perms = self.request.query_params.getlist(name)
        namespaces = get_objects_for_user(
            self.request.user, perms, klass=container_models.ContainerNamespace)
        return self.queryset.filter(namespace__in=namespaces)


class ManifestFilter(filterset.FilterSet):
    sort = filters.OrderingFilter(
        fields=(
            ('pulp_created', 'created'),
        ),
    )

    class Meta:
        model = container_models.Manifest
        # Tag filters are supported, but are done in get_queryset. See the comment
        # there
        fields = {
            'digest': ['exact', 'icontains', 'contains', 'startswith'],
        }


class HistoryFilter(filterset.FilterSet):
    sort = filters.OrderingFilter(
        fields=(
            ('pulp_created', 'created'),
            ('number', 'number'),
        ),
    )


class ContainerNamespaceViewSet(api_base.ModelViewSet):
    queryset = models.ContainerNamespace.objects.all()
    serializer_class = serializers.ContainerNamespaceDetailSerializer
    permission_classes = [access_policy.ContainerNamespaceAccessPolicy]
    lookup_field = "name"


class ContainerRepositoryViewSet(api_base.ModelViewSet):
    queryset = models.ContainerDistribution.objects.all().select_related('namespace')
    serializer_class = serializers.ContainerRepositorySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RepositoryFilter
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]
    lookup_field = "base_path"


# provide some common methods across all <distro>/_content/ endpoints
class ContainerContentBaseViewset(api_base.ModelViewSet):
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]

    def get_distro(self):
        return get_object_or_404(
            models.ContainerDistribution, base_path=self.kwargs["base_path"])


class ContainerRepositoryManifestViewSet(ContainerContentBaseViewset):
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ManifestFilter

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.ContainerManifestDetailSerializer
        return serializers.ContainerManifestSerializer

    def get_queryset(self):
        repo = self.get_distro().repository
        repo_version = repo.latest_version()
        repo_content = repo_version.content.all()

        manifests = (
            repo_version.get_content(container_models.Manifest.objects)
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
        )

        # I know that this should go in the FilterSet, but I cannot for the life
        # of me figure out how to access base_path in the filterset. Without
        # base_path, it's impossible to filter the tags down to a specific repo version,
        # which means this query would end up pulling all of the tags in all repos
        # that match the tag param, which could potentially be thousands of objects.
        tag_filter = self.request.GET.get('tag', None)
        if tag_filter:
            manifests = manifests.filter(
                # tagged_manifests doesn't respect the Prefetch filtering, so
                # the repo version has to be filtered again here
                tagged_manifests__pk__in=repo_version.get_content(
                    container_models.Tag.objects).filter(name__icontains=tag_filter))

        return manifests

    def get_object(self):
        qs = self.get_queryset()
        # manifest_ref can be a tag name or a manifest digest
        manifest_ref = self.kwargs['manifest_ref']
        try:
            repo_version = self.get_distro().repository.latest_version()

            # we could just return tag.tagged_manifest, but using the tag in the
            # queryset allows this to take advantage of all the prefetching that
            # happens in get_queryset
            tag = repo_version.get_content(container_models.Tag.objects).get(name=manifest_ref)
            manifest = qs.get(tagged_manifests__pk=tag)
        except exceptions.ObjectDoesNotExist:
            manifest = get_object_or_404(qs, digest=manifest_ref)

        return manifest


class ContainerRepositoryHistoryViewSet(ContainerContentBaseViewset):
    serializer_class = serializers.ContainerRepositoryHistorySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = HistoryFilter

    def get_queryset(self):
        repo = self.get_distro().repository

        allowed_content_types = ['container.manifest', 'container.tag']

        # The ui only cares about repo versions where tags and manifests are added.
        # Pulp container revs the repo version each time any blobs are added, so
        # this filters out any repo versions where tags and manifests are unchanged.
        return (
            repo.versions.annotate(
                # Count the number of added/removed manifests and tags and use
                # the result to filter out any versions where tags and manifests
                # are unchanged.
                added_count=Count('added_memberships', filter=Q(
                    added_memberships__content__pulp_type__in=allowed_content_types)),
                removed_count=Count('removed_memberships', filter=Q(
                    removed_memberships__content__pulp_type__in=allowed_content_types))
            )
            .filter(Q(added_count__gt=0) | Q(removed_count__gt=0))
            .prefetch_related(
                Prefetch(
                    'added_memberships',
                    queryset=core_models.RepositoryContent.objects.filter(
                        content__pulp_type__in=allowed_content_types).select_related('content'),
                ),
                Prefetch(
                    'removed_memberships',
                    queryset=core_models.RepositoryContent.objects.filter(
                        content__pulp_type__in=allowed_content_types).select_related('content'),
                )
            ).order_by('-pulp_created')
        )


class ContainerReadmeViewSet(ContainerContentBaseViewset):
    queryset = models.ContainerDistroReadme.objects
    serializer_class = serializers.ContainerReadmeSerializer
    permission_classes = [access_policy.ContainerReadmeAccessPolicy]

    def get_object(self):
        distro = self.get_distro()
        return self.queryset.get_or_create(container=distro)[0]
