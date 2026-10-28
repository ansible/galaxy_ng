from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("galaxy-ng")
except PackageNotFoundError:
    __version__ = "0+unknown"

default_app_config = "galaxy_ng.app.PulpGalaxyPluginAppConfig"
