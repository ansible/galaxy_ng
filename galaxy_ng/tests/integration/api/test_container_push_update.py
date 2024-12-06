"""Tests related to container push update.

See: https://issues.redhat.com/browse/AAH-2327
"""
import subprocess
import time

import pytest

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME
from galaxy_ng.tests.integration.utils import get_client
from galaxy_ng.tests.integration.utils.iqe_utils import pull_and_tag_test_image
from galaxykit.utils import wait_for_task


# FIXME(jerabekjiri): unskip when https://issues.redhat.com/browse/AAP-32675 is merged
@pytest.mark.skip_in_gw
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7.1")
@pytest.mark.min_hub_version("4.6.6")
def test_gw_can_update_container_push(ansible_config, galaxy_client):
    config = ansible_config("admin")
    container_engine = config["container_engine"]
    container_registry = config["container_registry"]
    # Pull alpine image
    pull_and_tag_test_image(container_engine, container_registry)

    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", f"{config['username']}", "-p",
           f"{config['password']}", container_registry]
    if container_engine == "podman":
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{container_registry}/alpine:latest"]
    if container_engine == "podman":
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Get an API client running with admin user credentials
    gc = galaxy_client("admin")

    # Get the pulp_href for the pushed repo
    image = gc.get("pulp/api/v3/repositories/container/container-push/?name=alpine", relogin=False)
    container_href = image["results"][0]["pulp_href"]

    for value in (42, 1):
        # Make a Patch request changing the retain_repo_versions attribute to value
        response = gc.patch(container_href, body={"retain_repo_versions": value}, relogin=False)

        resp = wait_for_task(gc, response)
        assert resp["state"] == "completed"

        # assert the change was persisted
        repo = gc.get(container_href)
        assert repo["retain_repo_versions"] == value


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
@pytest.mark.skip_in_gw
def test_can_update_container_push(ansible_config, require_auth):
    config = ansible_config("admin")
    container_engine = config["container_engine"]
    container_registry = config["container_registry"]
    # Pull alpine image
    pull_and_tag_test_image(container_engine, container_registry)

    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", f"{config['username']}", "-p",
           f"{config['password']}", container_registry]
    if container_engine == "podman":
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{container_registry}/alpine:latest"]
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
        time.sleep(SLEEP_SECONDS_ONETIME)
        # assert the change was persisted
        repo = client(container_href)
        assert repo["retain_repo_versions"] == value
