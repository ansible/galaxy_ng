from rest_framework import mixins
from rest_framework.exceptions import NotFound
from pulp_ansible.app.models import AnsibleDistribution
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from ..serializers.sync import CollectionRemoteSerializer


class SyncConfigViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = CollectionRemoteSerializer
    permission_classes = [access_policy.CollectionRemoteAccessPolicy]

    def get_object(self):
        """Resolve the CollectionRemote for this distribution path.

        has_model_or_obj_perms calls this for users without model permission, so
        missing or remote-less distributions must raise NotFound (404) instead of
        leaking DoesNotExist / AttributeError as 500s.
        """
        try:
            distribution = AnsibleDistribution.objects.get(base_path=self.kwargs['path'])
        except AnsibleDistribution.DoesNotExist:
            raise NotFound()

        repository = distribution.repository
        if not repository or not repository.remote:
            raise NotFound()

        return repository.remote.ansible_collectionremote
