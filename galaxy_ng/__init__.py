import sys
from ._vendor import automated_logging

sys.modules.setdefault("automated_logging", automated_logging)

__version__ = "4.10.0dev"

default_app_config = "galaxy_ng.app.PulpGalaxyPluginAppConfig"
