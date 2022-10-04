"""Tests related to container signing.

See: https://issues.redhat.com/browse/AAH-1358
"""
import subprocess
import time

import pytest

from galaxy_ng.tests.integration.utils import get_client


@pytest.fixture(scope="function")
def flags(ansible_config):
    api_client = get_client(config=ansible_config("admin"), request_token=True, require_auth=True)
    return api_client("/api/automation-hub/_ui/v1/feature-flags/")


@pytest.mark.standalone_only
def test_push_and_sign_a_container(ansible_config, flags):
    can_sign = flags.get("container_signing")
    if not can_sign:
        pytest.skip("GALAXY_CONTAINER_SIGNING_SERVICE is not configured")

    # Pull alpine image
    subprocess.check_call(["docker", "pull", "alpine"])
    # Tag the image
    subprocess.check_call(["docker", "tag", "alpine", "localhost:5001/alpine:latest"])

    # Login to local registy with tls verify disabled
    subprocess.check_call(["docker", "login", "-u", "admin", "-p", "admin", "localhost:5001"])
    # Push image to local registry
    subprocess.check_call(["docker", "push", "localhost:5001/alpine:latest"])

    # Get an API client running with admin user credentials
    client = get_client(config=ansible_config("admin"), request_token=True, require_auth=True)

    # Get the pulp_href for the pushed image
    image = client(
        "/api/automation-hub/pulp/api/v3/repositories/container/container-push/?name=alpine"
    )
    container_href = image["results"][0]["pulp_href"]

    # Get the pulp_href for signing service
    signing_service = client(
        "/api/automation-hub/pulp/api/v3/signing-services/?name=container-default"
    )
    ss_href = signing_service["results"][0]["pulp_href"]

    # Sign the image
    client(f"{container_href}/sign/", method="POST", args={"manifest_signing_service": ss_href})

    # sleep 2 second2
    time.sleep(2)

    repo = client(container_href)
    latest_version_href = repo["latest_version_href"]

    # Check the image is signed on the latest version
    latest_version = client(latest_version_href)
    assert latest_version["content_summary"]["added"]["container.signature"]["count"] > 0

    # Check the sign state is set on the UI API
    ee = client("/api/automation-hub/_ui/v1/execution-environments/repositories/?name=alpine")
    assert ee["data"][0]["pulp"]["repository"]["sign_state"] == "signed"
