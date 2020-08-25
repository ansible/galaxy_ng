from rest_framework import mixins
from pulp_ansible.app import models as pulp_models
from guardian.shortcuts import get_objects_for_user

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers, versioning
from galaxy_ng.app.api import base as api_base


class DistributionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    api_base.GenericViewSet,
):
    serializer_class = serializers.DistributionSerializer
    model = pulp_models.AnsibleDistribution
    queryset = pulp_models.AnsibleDistribution.objects.exclude(name__startswith='inbound-')
    # TODO: add access policy
    # permission_classes = [access_policy.UserAccessPolicy]
    versioning_class = versioning.UIVersioning

# TODO: add my distribution once I figure out how to link a synclist to a distribution
# class MyDistributionViewSet(DistributionViewSet):
#
#     def get_queryset(self):
#         synclists = get_objects_for_user(
#             self.request.user,
#             'galaxy.change_synclist',
#             any_perm=True,
#             klass=models.SyncList
#         )
