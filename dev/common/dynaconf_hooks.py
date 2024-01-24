from dynaconf.utils.parse_conf import parse_conf_data
from dynaconf.vendor.dotenv import dotenv_values


def post(settings):
    """This is file is meant to be used only on dev environment

    The main goal is to:
    - load `.compose.env` file values and override the settings with those values
      whenever the application restarts
    - The docker API container is set to restart when .compose.env changes.
    """
    data = {
        k[5:]: parse_conf_data(v, tomlfy=True, box_settings=settings)
        for k, v in dotenv_values("/app/.compose.env").items()
        if k.startswith("PULP_")
    }
    return data
