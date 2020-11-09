from galaxy_ng.app.constants import COMMUNITY_DOMAINS
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from django.shortcuts import get_object_or_404

from pulp_ansible.app import models as pulp_models
from pulp_ansible.app.tasks.collections import sync as collection_sync

from pulpcore.plugin.tasking import enqueue_with_reservation
from pulpcore.plugin.models import Task

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app import models


class SyncRemoteView(api_base.APIView):
    permission_classes = [access_policy.CollectionRemoteAccessPolicy]
    action = 'sync'

    def post(self, request: Request, *args, **kwargs) -> Response:
        distro_path = kwargs['path']
        distro = get_object_or_404(pulp_models.AnsibleDistribution, base_path=distro_path)

        if not distro.repository or not distro.repository.remote:
            raise ValidationError(
                detail={'remote': f'The {distro_path} distribution does not have'
                                  ' any remotes associated with it.'})

        remote = distro.repository.remote.ansible_collectionremote

        if not remote.requirements_file and any(
            [domain in remote.url for domain in COMMUNITY_DOMAINS]
        ):
            raise ValidationError(
                detail={
                    'requirements_file':
                        'Syncing content from galaxy.ansible.com without specifying a '
                        'requirements file is not allowed.'
                })

        result = enqueue_with_reservation(
            collection_sync,
            [distro.repository, remote],
            kwargs={
                "remote_pk": remote.pk,
                "repository_pk": distro.repository.pk,
                "mirror": True
            },
        )

        repo = pulp_models.AnsibleRepository.objects.get(pk=distro.repository.pk)
        task = Task.objects.get(pk=result.id)

        models.CollectionSyncTask.objects.create(
            repository=repo,
            task=task
        )

        return Response({'task': task.pk})
