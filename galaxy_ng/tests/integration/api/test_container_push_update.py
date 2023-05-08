
"""Tests related to container push update.
See: https://issues.redhat.com/browse/AAH-2327
"""
import subprocess
import time

import pytest

from galaxy_ng.tests.integration.utils import get_client


@pytest.mark.parametrize(
    "require_auth",
    [
        True,
        False,
    ],
)
@pytest.mark.standalone_only
def test_can_update_container_push(ansible_config, require_auth):
    # Pull alpine image
    subprocess.check_call(["docker", "pull", "alpine"])
    # Tag the image
    subprocess.check_call(["docker", "tag", "alpine", "localhost:5001/alpine:latest"])

    # Login to local registy with tls verify disabled
    subprocess.check_call(["docker", "login", "-u", "admin", "-p", "admin", "localhost:5001"])
    # Push image to local registry
    subprocess.check_call(["docker", "push", "localhost:5001/alpine:latest"])

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
