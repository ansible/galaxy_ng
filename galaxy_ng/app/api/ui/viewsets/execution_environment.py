import logging

from django.core import exceptions
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django_filters import filters
from django_filters.rest_framework import DjangoFilterBackend, filterset
from drf_spectacular.utils import extend_schema
from pulpcore.plugin.util import get_objects_for_user
from pulp_container.app import models as container_models
from pulpcore.plugin import models as core_models
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import OperationPostponedResponse

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.tasks.deletion import (
    delete_container_distribution,
    delete_container_image_manifest,
)

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
            self.request.user, perms, qs=container_models.ContainerNamespace.objects.all())
        return self.queryset.filter(namespace__in=namespaces)


class ManifestFilter(filterset.FilterSet):
    exclude_child_manifests = filters.BooleanFilter(method='filter_child_manifests')

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

    def filter_child_manifests(self, queryset, name, value):
        if value:
            return queryset.annotate(num_parents=Count("manifest_lists")).exclude(num_parents__gt=0)
        else:
            return queryset


class TagFilter(filterset.FilterSet):
    sort = filters.OrderingFilter(
        fields=(
            ("pulp_created", "pulp_created"),
            ("pulp_last_updated", "pulp_last_updated"),
            ("name", "name"),
        ),
    )

    class Meta:
        model = container_models.Tag
        # Tag filters are supported, but are done in get_queryset. See the comment
        # in ContainerRepositoryManifestViewSet.get_queryset
        fields = {
            "name": ["exact", "icontains", "contains", "startswith"],
            "tagged_manifest__digest": ["exact", "icontains", "contains", "startswith"],
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

    @extend_schema(
        description="Trigger an asynchronous delete task",
        responses={202: AsyncOperationResponseSerializer},
    )
    def destroy(self, request, *args, **kwargs):
        """
        Delete a distribution. If a push repository is associated to it, delete it as well.
        Perform orphan cleanup.
        """
        distribution = self.get_object()
        reservations = [distribution]
        ids_for_multi_delete = [
            (str(distribution.pk), "container", "ContainerDistributionSerializer"),
        ]
        if distribution.repository:
            reservations.append(distribution.repository)

            if distribution.repository.cast().PUSH_ENABLED:
                ids_for_multi_delete.append(
                    (str(distribution.repository.pk), "container",
                        "ContainerPushRepositorySerializer"),
                )
            else:
                ids_for_multi_delete.append(
                    (str(distribution.repository.pk), "container",
                        "ContainerRepositorySerializer"),
                )

            if distribution.repository.remote:
                reservations.append(distribution.repository.remote)
                ids_for_multi_delete.append(
                    (str(distribution.repository.remote.pk), "container",
                        "ContainerRemoteSerializer"),
                )

        # Delete the distribution, repository, and perform orphan cleanup
        async_result = dispatch(
            delete_container_distribution,
            args=(ids_for_multi_delete,),
            exclusive_resources=reservations
        )

        return OperationPostponedResponse(async_result, request)


# provide some common methods across all <distro>/_content/ endpoints
class ContainerContentBaseViewset(api_base.ModelViewSet):
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]

    def get_distro(self):
        if getattr(self, "swagger_fake_view", False):
            # OpenAPI will generate a fake view with this attribute set
            return models.ContainerDistribution.objects.none()
        return get_object_or_404(
            models.ContainerDistribution, base_path=self.kwargs["base_path"])


class ContainerTagViewset(ContainerContentBaseViewset):
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]
    serializer_class = serializers.ContainerTagSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TagFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # OpenAPI will generate a fake view with this attribute set
            return container_models.Tag.objects.none()
        repo = self.get_distro().repository
        repo_version = repo.latest_version()
        return repo_version.get_content(container_models.Tag.objects)


class ContainerRepositoryManifestViewSet(ContainerContentBaseViewset):
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ManifestFilter

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return serializers.ContainerManifestDetailSerializer
        return serializers.ContainerManifestSerializer

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # OpenAPI will generate a fake view with this attribute set
            return container_models.Manifest.objects.none()
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

    @extend_schema(
        description=(
            "Trigger an asynchronous task to remove a manifest and all its associated "
            "data by a digest"
        ),
        summary="Delete an image from a repository",
        responses={202: AsyncOperationResponseSerializer},
    )
    def destroy(self, request, *args, **kwargs):
        """Deletes a image manifest.

        - Looks up the image via a sha
        - Remove all tags that point to the selected manifest from the latest version of the repo.
        - Remove the selected image manifest from the selected repository using the pulp container
          remove_image function: This function will remove the manifest from the latest version
          of the repository and any blobs associated with the manifest that aren’t used by
          other manifests.
        - Call the reclaim disk space function on the selected repository, with the latest version
          of the repository preserved. This will clear out artifacts for content that isn’t in the
          latest version of the repository.
        """
        # Looks up the image via a sha
        manifest = self.get_object()
        repository = self.get_distro().repository
        latest_version = repository.latest_version()

        # Remove all tags that point to the selected manifest from the latest version of the repo.
        tags_pks = container_models.Tag.objects.filter(
            pk__in=latest_version.content.all(), tagged_manifest=manifest
        ).values_list("pk", flat=True)

        # Remove the selected image manifest from the selected repository using the pulp container
        content_unit_pks = [str(pk) for pk in list(tags_pks) + [manifest.pk]]

        # Call the recursive_remove_content from pulp_container + reclaim disk space
        async_result = dispatch(
            delete_container_image_manifest,
            args=(str(repository.pk), content_unit_pks, str(latest_version.pk)),
            exclusive_resources=[repository],
        )

        return OperationPostponedResponse(async_result, request)


class ContainerRepositoryHistoryViewSet(ContainerContentBaseViewset):
    serializer_class = serializers.ContainerRepositoryHistorySerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = HistoryFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            # OpenAPI will generate a fake view with this attribute set
            return core_models.RepositoryVersion.objects.none()
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


class ContainerRegistryRemoteViewSet(api_base.ModelViewSet):
    queryset = models.ContainerRegistryRemote.objects.all()
    serializer_class = serializers.ContainerRegistryRemoteSerializer
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    filterset_class = ContainerRegistryRemoteFilter


class ContainerRemoteViewSet(api_base.ModelViewSet):
    queryset = container_models.ContainerRemote.objects.all()
    serializer_class = serializers.ContainerRemoteSerializer
    permission_classes = [access_policy.ContainerRemoteAccessPolicy]
