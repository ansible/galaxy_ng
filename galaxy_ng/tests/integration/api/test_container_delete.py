from galaxy_ng.tests.integration.api.rbac_actions.utils import ensure_test_container_is_pulled
import requests
import subprocess
from galaxy_ng.tests.integration.utils import get_client
import pytest


def delete_ee_and_content(user, password, ansible_config):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=False, require_auth=True)

    # Pull alpine image
    subprocess.check_call(["podman", "pull", "alpine"])

    # Tag the image
    subprocess.check_call(["podman", "tag", "alpine", "localhost:5001/alpine:latest"])

    # Go to the container distribution list and select the distribution via the base path.
    response_distro = requests.get(
        f"{api_prefix}/api/automation-hub/pulp/api/v3/distributions/container/container/?base_path=alpine",
        auth=(user['username'], password),
    )
    assert response_distro["results"]["base_path"] == 'alpine'

    # Grab the repository href from the json
    repo_href = response_distro["results"]["repository"]
