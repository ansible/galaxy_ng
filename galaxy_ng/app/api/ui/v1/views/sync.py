from rest_framework.request import Request
from rest_framework.response import Response

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from pulpcore.plugin.viewsets import (
    OperationPostponedResponse,
)
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app import models, tasks


class ContainerSyncRegistryView(api_base.APIView):
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    action = 'sync'

    @extend_schema(
        description="Trigger an asynchronous sync task",
        responses={202: AsyncOperationResponseSerializer},
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        registry = get_object_or_404(models.ContainerRegistryRemote, pk=kwargs['id'])

        result = dispatch(
            tasks.sync_all_repos_in_registry,
            kwargs={
                "registry_pk": str(registry.pk),
            },
            exclusive_resources=[registry]
        )
        return OperationPostponedResponse(result, request)
