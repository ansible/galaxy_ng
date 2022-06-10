from pulpcore.plugin import viewsets as pulp_viewsets
from rest_framework import mixins

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.access_control.statements.roles import LOCKED_ROLES as GALAXY_LOCKED_ROLES
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.api.v3.serializers import NamespaceSummarySerializer

# This file is necesary to prevent the DRF web API browser from breaking on all of the
# pulp/api/v3/repositories/ endpoints.

# Pulp expects models it manages to come with a viewset attached to them. Since the
# ContainerRegistryRemote model is a pulp remote, pulp expects it to have a pulp
# viewset attached to it. Pulp associates viewsets with models by looking in
# <plugin_name>.app.viewsets. Since galaxy_ng stores it's viewsets in a different
# module, this file is necesary for pulp tbe able to associate the ContainerRegistryRemote
# model to a viewset.

# Without this viewset defined here, pulp get's confused when it tries to auto generate
# the form on the repositories endpoint because it tries to provide a dropdown
# on the remote field and can't find a viewset name for galaxy's ContainerRegistryRemote model.


# Added to keep the DRF forms from breaking
class ContainerRegistryRemoteViewSet(
    pulp_viewsets.NamedModelViewSet,
    mixins.RetrieveModelMixin,
):
    queryset = models.ContainerRegistryRemote.objects.all()
    serializer_class = serializers.ContainerRegistryRemoteSerializer
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    endpoint_name = "galaxy_ng/registry-remote"
    LOCKED_ROLES = GALAXY_LOCKED_ROLES


# Added to keep the DRF forms from breaking
class ContainerDistributionViewSet(
    pulp_viewsets.NamedModelViewSet,
    mixins.RetrieveModelMixin,
):
    queryset = models.ContainerDistribution.objects.all()
    serializer_class = serializers.ContainerRepositorySerializer
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]
    endpoint_name = "galaxy_ng/container-distribution-proxy"


# added so that object permissions are viewable for namespaces on the roles api endpoint.
class NamespaceViewSet(
    pulp_viewsets.NamedModelViewSet,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
):
    queryset = models.Namespace.objects.all()
    serializer_class = NamespaceSummarySerializer
    permission_classes = [access_policy.NamespaceAccessPolicy]
    endpoint_name = "pulp_ansible/namespaces"


# This is here because when new objects are created, pulp tries to look up the viewset for
# the model so that it can run creation hooks to assign permissions. This function fails
# if the model isn't registered with a pulp viewset
# https://github.com/pulp/pulpcore/blob/52c8e16997849b9a639aec04945cec98486d54fb/pulpcore
#   /app/models/access_policy.py#L73
class GroupViewset(
    pulp_viewsets.NamedModelViewSet,
):
    queryset = models.auth.Group.objects.all()
    endpoint_name = "galaxy_ng/sgroups"
