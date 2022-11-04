from typing import Any, Dict
from dynaconf import Dynaconf


def configure_pulp_ansible(settings: Dynaconf) -> Dict[str, Any]:
    # Translate the galaxy default base path to the pulp ansible default base path.
    distro_path = settings.get("GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH", "published")

    return {
        # ANSIBLE_URL_NAMESPACE tells pulp_ansible to generate hrefs and redirects that
        # point to the galaxy_ng api namespace. We're forcing it to get set to our api
        # namespace here because setting it to anything else will break our api.
        "ANSIBLE_URL_NAMESPACE": "galaxy:api:v3:",
        "ANSIBLE_DEFAULT_DISTRIBUTION_PATH": distro_path
    }
