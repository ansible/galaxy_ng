from galaxy_ng.app.constants import COMMUNITY_DOMAINS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema

from pulp_ansible.app import models as pulp_models
from pulp_ansible.app.tasks.collections import sync as collection_sync

from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy


class SyncRemoteView(api_base.APIView):
    permission_classes = [access_policy.CollectionRemoteAccessPolicy]
    action = 'sync'

    @extend_schema(
        description="Trigger an asynchronous sync task",
        responses={202: AsyncOperationResponseSerializer},
    )
    def post(self, request: Request, *args, **kwargs) -> Response:
        distro_path = kwargs['path']
        distro = get_object_or_404(pulp_models.AnsibleDistribution, base_path=distro_path)

        if not distro.repository or not distro.repository.remote:
            raise ValidationError(
                detail={'remote': _('The %s distribution does not have'
                                    ' any remotes associated with it.') % distro_path})

        remote = distro.repository.remote.ansible_collectionremote

        if not remote.requirements_file and any(
            [domain in remote.url for domain in COMMUNITY_DOMAINS]
        ):
            raise ValidationError(
                detail={
                    'requirements_file':
                        _('Syncing content from galaxy.ansible.com without specifying a '
                          'requirements file is not allowed.')
                })

        result = dispatch(
            collection_sync,
            kwargs={
                "remote_pk": remote.pk,
                "repository_pk": distro.repository.pk,
                "mirror": True,
                "optimize": True,
            },
            exclusive_resources=[distro.repository, remote],
        )

        return Response({'task': result.pk})
