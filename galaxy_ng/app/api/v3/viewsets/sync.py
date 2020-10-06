from rest_framework import mixins
from django.http import Http404
from pulp_ansible.app.models import AnsibleDistribution
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.models import CollectionSyncTask
from ..serializers.sync import SyncConfigSerializer, SyncTaskSerializer


class SyncConfigViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = SyncConfigSerializer
    permission_classes = [access_policy.CollectionRemoteAccessPolicy]

    def get_object(self):
        distribution = AnsibleDistribution.objects.get(base_path=self.kwargs['path'])
        if distribution and distribution.repository:
            return distribution.repository.remote.ansible_collectionremote
        raise Http404


class SyncTaskViewSet(api_base.ModelViewSet):
    """List of Synchronization tasks spawned for collections."""

    serializer_class = SyncTaskSerializer
    permission_classes = [access_policy.CollectionRemoteAccessPolicy]
    model = CollectionSyncTask

    def get_queryset(self):
        distribution = AnsibleDistribution.objects.get(base_path=self.kwargs['path'])
        if distribution and distribution.repository:
            return CollectionSyncTask.objects.filter(repository=distribution.repository)
        raise Http404
