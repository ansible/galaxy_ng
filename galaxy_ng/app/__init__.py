from pulpcore.plugin import PulpPluginAppConfig


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "galaxy_ng.app"
    label = "galaxy"
