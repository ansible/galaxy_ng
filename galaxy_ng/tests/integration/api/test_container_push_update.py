"""Tests related to container push update.

See: https://issues.redhat.com/browse/AAH-2327
"""
import subprocess
import time
from urllib.parse import urlparse

import pytest

from galaxy_ng.tests.integration.utils import get_client
from galaxy_ng.tests.integration.utils.iqe_utils import pull_and_tag_test_image


@pytest.mark.parametrize(
    "require_auth",
    [
        True,
        False,
    ],
)
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7.1")
@pytest.mark.min_hub_version("4.6.6")
def test_can_update_container_push(ansible_config, require_auth):
    config = ansible_config("admin")
    container_engine = config["container_engine"]
    url = config['url']
    parsed_url = urlparse(url)
    cont_reg = parsed_url.netloc
    # Pull alpine image
    pull_and_tag_test_image(container_engine, cont_reg)

    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", f"{config['username']}", "-p",
           f"{config['password']}", f"{config['url'].split(parsed_url.path)[0]}"]
    if container_engine == "podman":
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{cont_reg}/alpine:latest"]
    if container_engine == "podman":
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Get an API client running with admin user credentials
    client = get_client(
        config=ansible_config("admin"),
        request_token=True,
        require_auth=require_auth
    )
    api_prefix = client.config.get("api_prefix").rstrip("/")

    # Get the pulp_href for the pushed repo
    image = client(
        f"{api_prefix}/pulp/api/v3/repositories/container/container-push/?name=alpine"
    )
    container_href = image["results"][0]["pulp_href"]

    for value in (42, 1):
        # Make a Patch request changing the retain_repo_versions attribute to value
        client(container_href, method="PATCH", args={"retain_repo_versions": value})

        # sleep 2 seconds waiting task to finish
        time.sleep(2)
        # assert the change was persisted
        repo = client(container_href)
        assert repo["retain_repo_versions"] == value
