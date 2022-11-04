from typing import Any, Dict
from dynaconf import Dynaconf


def configure_api_base_path(settings: Dynaconf) -> Dict[str, Any]:
    """Set the pulp api root under the galaxy api root."""

    galaxy_api_root = settings.get("GALAXY_API_PATH_PREFIX")
    pulp_api_root = f"/{galaxy_api_root.strip('/')}/pulp/"
    return {"API_ROOT": pulp_api_root}
