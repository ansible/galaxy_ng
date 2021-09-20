from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from pulp_container.app import models as pulp_models
from pulp_container.app.tasks.synchronize import synchronize as container_sync
from pulpcore.plugin.viewsets import (
    OperationPostponedResponse,
)
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app import models


class ContainerSyncRemoteView(api_base.APIView):
    permission_classes = [access_policy.ContainerRemoteSyncAccessPolicy]
    action = 'sync'

    def post(self, request: Request, *args, **kwargs) -> Response:
        distro_path = kwargs['base_path']
        distro = get_object_or_404(pulp_models.ContainerDistribution, base_path=distro_path)

        if not distro.repository or not distro.repository.remote:
            raise ValidationError(
                detail={'remote': _('The %s distribution does not have'
                                    ' any remotes associated with it.') % distro_path})

        remote = distro.repository.remote.cast()

        try:
            registry = remote.registry.registry
        except models.ContainerRegistryRepos.repository_remote.RelatedObjectDoesNotExist:
            raise ValidationError(
                detail={'remote': _('The %s remote does not have'
                                    ' any registries associated with it.') % distro_path}
            )

        for key, value in registry.get_connection_fields().items():
            setattr(remote, key, value)
        remote.save()

        result = dispatch(
            container_sync,
            shared_resources=[remote],
            exclusive_resources=[distro.repository],
            kwargs={
                "remote_pk": str(remote.pk),
                "repository_pk": str(distro.repository.pk),
                "mirror": True,
            },
        )
        return OperationPostponedResponse(result, request)
