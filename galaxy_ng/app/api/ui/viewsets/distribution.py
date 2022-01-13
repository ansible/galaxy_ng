from rest_framework import mixins
from pulp_ansible.app import models as pulp_models
from pulpcore.plugin.util import get_objects_for_user

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers, versioning
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app import models


class DistributionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = serializers.DistributionSerializer
    model = pulp_models.AnsibleDistribution
    queryset = pulp_models.AnsibleDistribution.objects.exclude(
        name__startswith='inbound-').exclude(
            name__endswith='-synclist').order_by('name')
    permission_classes = [access_policy.DistributionAccessPolicy]
    versioning_class = versioning.UIVersioning


class MyDistributionViewSet(DistributionViewSet):
    permission_classes = [access_policy.MyDistributionAccessPolicy]

    def get_queryset(self):
        synclists = get_objects_for_user(
            self.request.user,
            'galaxy.change_synclist',
            any_perm=True,
            accept_global_perms=False,
            qs=models.SyncList.objects.all()
        )

        # TODO: find a better way query this data
        return pulp_models.AnsibleDistribution.objects.filter(
            name__in=synclists.values_list('name', flat=True)).order_by('name')
