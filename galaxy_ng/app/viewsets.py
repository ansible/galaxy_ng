from pulpcore.plugin import viewsets as pulp_viewsets
from rest_framework import mixins

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers

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


class ContainerRegistryRemoteViewSet(pulp_viewsets.NamedModelViewSet, mixins.RetrieveModelMixin):
    queryset = models.ContainerRegistryRemote.objects.all()
    serializer_class = serializers.ContainerRegistryRemoteSerializer
    permission_classes = [access_policy.ContainerRegistryRemoteAccessPolicy]
    endpoint_name = "execution-environments-registry-detail"


class ContainerDistributionViewSet(
    pulp_viewsets.NamedModelViewSet,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
):
    queryset = models.ContainerDistribution.objects.all()
    serializer_class = serializers.ContainerRepositorySerializer
    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]
    endpoint_name = "container"
