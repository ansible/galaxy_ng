import os
from pulpcore.plugin import PulpPluginAppConfig

with open(os.path.join(os.path.dirname(__file__), 'VERSION')) as version_file:
    galaxy_ng_version = version_file.read()


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "galaxy_ng.app"
    label = "galaxy"
    version = galaxy_ng_version
