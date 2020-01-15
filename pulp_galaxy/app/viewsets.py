"""
Check `Plugin Writer's Guide`_ for more details.

.. _Plugin Writer's Guide:
    http://docs.pulpproject.org/en/3.0/nightly/plugins/plugin-writer/index.html
"""

from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from pulpcore.app.viewsets import RemoteFilter
from pulpcore.plugin import viewsets as core
from pulpcore.plugin.actions import ModifyRepositoryActionMixin
from pulpcore.plugin.serializers import (
    AsyncOperationResponseSerializer,
    RepositorySyncURLSerializer,
)
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.models import ContentArtifact

from . import models, serializers, tasks


class GalaxyContentFilter(core.ContentFilter):
    """
    FilterSet for GalaxyContent.
    """

    class Meta:
        model = models.GalaxyContent
        fields = [
            # ...
        ]


class GalaxyContentViewSet(core.ContentViewSet):
    """
    A ViewSet for GalaxyContent.

    Define endpoint name which will appear in the API endpoint for this content type.
    For example::
        http://pulp.example.com/pulp/api/v3/content/galaxy/units/

    Also specify queryset and serializer for GalaxyContent.
    """

    endpoint_name = "galaxy"
    queryset = models.GalaxyContent.objects.all()
    serializer_class = serializers.GalaxyContentSerializer
    filterset_class = GalaxyContentFilter

    @transaction.atomic
    def create(self, request):
        """
        Perform bookkeeping when saving Content.

        "Artifacts" need to be popped off and saved indpendently, as they are not actually part
        of the Content model.
        """
        raise NotImplementedError("FIXME")
        # This requires some choice. Depending on the properties of your content type - whether it
        # can have zero, one, or many artifacts associated with it, and whether any properties of
        # the artifact bleed into the content type (such as the digest), you may want to make
        # those changes here.

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # A single artifact per content, serializer subclasses SingleArtifactContentSerializer
        # ======================================
        # _artifact = serializer.validated_data.pop("_artifact")
        # # you can save model fields directly, e.g. .save(digest=_artifact.sha256)
        # content = serializer.save()
        #
        # if content.pk:
        #     ContentArtifact.objects.create(
        #         artifact=artifact,
        #         content=content,
        #         relative_path= ??
        #     )
        # =======================================

        # Many artifacts per content, serializer subclasses MultipleArtifactContentSerializer
        # =======================================
        # _artifacts = serializer.validated_data.pop("_artifacts")
        # content = serializer.save()
        #
        # if content.pk:
        #   # _artifacts is a dictionary of {"relative_path": "artifact"}
        #   for relative_path, artifact in _artifacts.items():
        #       ContentArtifact.objects.create(
        #           artifact=artifact,
        #           content=content,
        #           relative_path=relative_path
        #       )
        # ========================================

        # No artifacts, serializer subclasses NoArtifactContentSerialier
        # ========================================
        # content = serializer.save()
        # ========================================

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class GalaxyRemoteFilter(RemoteFilter):
    """
    A FilterSet for GalaxyRemote.
    """

    class Meta:
        model = models.GalaxyRemote
        fields = [
            # ...
        ]


class GalaxyRemoteViewSet(core.RemoteViewSet):
    """
    A ViewSet for GalaxyRemote.

    Similar to the GalaxyContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "galaxy"
    queryset = models.GalaxyRemote.objects.all()
    serializer_class = serializers.GalaxyRemoteSerializer


class GalaxyRepositoryViewSet(core.RepositoryViewSet, ModifyRepositoryActionMixin):
    """
    A ViewSet for GalaxyRepository.

    Similar to the GalaxyContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "galaxy"
    queryset = models.GalaxyRepository.objects.all()
    serializer_class = serializers.GalaxyRepositorySerializer

    # This decorator is necessary since a sync operation is asyncrounous and returns
    # the id and href of the sync task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to sync content.",
        operation_summary="Sync from remote",
        responses={202: AsyncOperationResponseSerializer},
    )
    @action(detail=True, methods=["post"], serializer_class=RepositorySyncURLSerializer)
    def sync(self, request, pk):
        """
        Dispatches a sync task.
        """
        repository = self.get_object()
        serializer = RepositorySyncURLSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        remote = serializer.validated_data.get("remote")

        result = enqueue_with_reservation(
            tasks.synchronize,
            [repository, remote],
            kwargs={"remote_pk": remote.pk, "repository_pk": repository.pk},
        )
        return OperationPostponedResponse(result, request)


class GalaxyRepositoryVersionViewSet(core.RepositoryVersionViewSet):
    """
    A ViewSet for a GalaxyRepositoryVersion represents a single
    Galaxy repository version.
    """

    parent_viewset = GalaxyRepositoryViewSet


class GalaxyPublicationViewSet(core.PublicationViewSet):
    """
    A ViewSet for GalaxyPublication.

    Similar to the GalaxyContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "galaxy"
    queryset = models.GalaxyPublication.objects.all()
    serializer_class = serializers.GalaxyPublicationSerializer

    # This decorator is necessary since a publish operation is asyncrounous and returns
    # the id and href of the publish task.
    @swagger_auto_schema(
        operation_description="Trigger an asynchronous task to publish content",
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request):
        """
        Publishes a repository.

        Either the ``repository`` or the ``repository_version`` fields can
        be provided but not both at the same time.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repository_version = serializer.validated_data.get("repository_version")

        result = enqueue_with_reservation(
            tasks.publish,
            [repository_version.repository],
            kwargs={"repository_version_pk": str(repository_version.pk),},
        )
        return core.OperationPostponedResponse(result, request)


class GalaxyDistributionViewSet(core.BaseDistributionViewSet):
    """
    A ViewSet for GalaxyDistribution.

    Similar to the GalaxyContentViewSet above, define endpoint_name,
    queryset and serializer, at a minimum.
    """

    endpoint_name = "galaxy"
    queryset = models.GalaxyDistribution.objects.all()
    serializer_class = serializers.GalaxyDistributionSerializer
