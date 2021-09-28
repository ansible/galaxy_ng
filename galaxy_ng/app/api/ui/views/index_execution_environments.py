from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status

from drf_spectacular.utils import extend_schema

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app import models
from galaxy_ng.app import tasks


class IndexRegistryEEView(api_base.APIView):
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    action = 'index_execution_environments'

    @extend_schema(
        description="Trigger an asynchronous indexing task",
        responses={status.HTTP_202_ACCEPTED: AsyncOperationResponseSerializer},
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        registry = get_object_or_404(models.ContainerRegistryRemote, pk=kwargs['pk'])

        if not registry.get_registry_backend():
            raise ValidationError(
                detail={
                    'url':
                        _('Indexing execution environments is not supported on this registry.')
                })

        serializable_meta = {}
        for key in self.request.META:
            val = self.request.META[key]
            if type(val) == str:
                serializable_meta[key] = val

        request_data = {
            "META": serializable_meta,
        }

        result = dispatch(
            tasks.index_execution_environments_from_redhat_registry,
            kwargs={
                "registry_pk": registry.pk,
                "request_data": request_data
            },
        )

        return OperationPostponedResponse(result, self.request)
