import logging


log = logging.getLogger(__name__)

viewsets = {
    # name :  source module
    "ContainerRegistryRemoteViewSet": "galaxy_ng.app.api.ui.viewsets.execution_environment",
    "ContainerDistributionViewSet": "pulp_container.app.viewsets",
}


def __getattr__(self, name):
    """
    This is a hack to get pulp to associate the model with a viewset.

    This file is necessary to prevent the DRF web API browser from breaking on all of the
    pulp/api/v3/repositories/ endpoints.
    Pulp expects models it manages to come with a viewset attached to them. Since the
    ContainerRegistryRemote model is a pulp remote, pulp expects it to have a NamedModelViewSet
    viewset attached to it. Pulp associates viewsets with models by looking in
    <plugin_name>.app.viewsets. Since galaxy_ng stores it's viewsets in a different
    module, this file is necesary for pulp tbe able to associate the ContainerRegistryRemote
    model to a viewset.
    Without this viewset defined here, pulp gets confused when it tries to auto generate
    the form on the repositories endpoint because it tries to provide a dropdown
    on the remote field and can't find a viewset name for galaxy's ContainerRegistryRemote model.

    """

    if name in viewsets:
        try:
            module = __import__(viewsets[name])
        except ImportError as e:
            log.error("Error importing viewset: %s" % e)
        else:
            return getattr(module, name)

    log.warning("No viewset found for model %s", name)
    raise AttributeError(name)
