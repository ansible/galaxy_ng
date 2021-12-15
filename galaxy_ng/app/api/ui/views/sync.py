from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema

from pulp_container.app import models as pulp_models
from pulpcore.plugin.viewsets import (
    OperationPostponedResponse,
)
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app import models, tasks


class ContainerSyncRemoteView(api_base.APIView):
    permission_classes = [access_policy.ContainerRemoteAccessPolicy]
    action = 'sync'

    def get_object(self):
        """Object is a ContainerRemote instance"""
        distro = self.get_distribution()
        remote = distro.repository.remote.cast()
        return remote

    def get_distribution(self):
        distro_path = self.kwargs['base_path']
        distro = get_object_or_404(pulp_models.ContainerDistribution, base_path=distro_path)

        if not distro.repository or not distro.repository.remote:
            raise ValidationError(
                detail={'remote': _('The %s distribution does not have'
                                    ' any remotes associated with it.') % distro_path})

        return distro

    def post(self, request: Request, *args, **kwargs) -> Response:
        distro_path = kwargs['base_path']
        distro = self.get_distribution()
        remote = distro.repository.remote.cast()

        try:
            registry = remote.registry.registry
        except models.ContainerRegistryRepos.repository_remote.RelatedObjectDoesNotExist:
            raise ValidationError(
                detail={'remote': _('The %s remote does not have'
                                    ' any registries associated with it.') % distro_path}
            )

        result = tasks.launch_container_remote_sync(remote, registry, distro.repository)
        return OperationPostponedResponse(result, request)


class ContainerSyncRegistryView(api_base.APIView):
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    action = 'sync'

    @extend_schema(
        description="Trigger an asynchronous sync task",
        responses={202: AsyncOperationResponseSerializer},
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        registry = get_object_or_404(models.ContainerRegistryRemote, pk=kwargs['pk'])

        result = dispatch(
            tasks.sync_all_repos_in_registry,
            kwargs={
                "registry_pk": str(registry.pk),
            },
            exclusive_resources=[registry]
        )
        return OperationPostponedResponse(result, request)
