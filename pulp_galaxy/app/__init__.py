from pulpcore.plugin import PulpPluginAppConfig


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "pulp_galaxy.app"
    label = "galaxy"
