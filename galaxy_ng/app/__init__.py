from pulpcore.plugin import PulpPluginAppConfig


class PulpGalaxyPluginAppConfig(PulpPluginAppConfig):
    """Entry point for the galaxy plugin."""

    name = "galaxy_ng.app"
    label = "galaxy"
    version = "4.6.1"
    python_package_name = "galaxy-ng"

    def ready(self):
        super().ready()
        from .signals import handlers  # noqa
