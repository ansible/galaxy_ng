"""Tests related to container signing.

See: https://issues.redhat.com/browse/AAH-1358
"""
import subprocess
import time

import pytest

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME
from galaxy_ng.tests.integration.utils import get_client
from galaxy_ng.tests.integration.utils.iqe_utils import pull_and_tag_test_image
from galaxykit.container_images import get_container
from galaxykit.utils import wait_for_task


@pytest.fixture
def flags(galaxy_client):
    gc = galaxy_client("admin")
    return gc.get("_ui/v1/feature-flags/")


@pytest.mark.deployment_standalone
def test_gw_push_and_sign_a_container(ansible_config, flags, galaxy_client):
    can_sign = flags.get("container_signing")
    if not can_sign:
        pytest.skip("GALAXY_CONTAINER_SIGNING_SERVICE is not configured")

    config = ansible_config("admin")
    container_engine = config["container_engine"]
    container_registry = config["container_registry"]

    # Pull alpine image
    pull_and_tag_test_image(container_engine, container_registry)

    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", f"{config['username']}", "-p",
           f"{config['password']}", container_registry]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{container_registry}/alpine:latest"]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Get an API client running with admin user credentials
    gc = galaxy_client("admin")
    # Get the pulp_href for the pushed image
    image = gc.get("pulp/api/v3/repositories/container/container-push/?name=alpine", relogin=False)
    container_href = image["results"][0]["pulp_href"]

    # Get the pulp_href for signing service

    signing_service = gc.get("pulp/api/v3/signing-services/?name=container-default", relogin=False)
    ss_href = signing_service["results"][0]["pulp_href"]

    # Sign the image
    r = gc.post(f"{container_href}sign/", body={"manifest_signing_service": ss_href}, relogin=False)
    resp = wait_for_task(gc, r)
    assert resp["state"] == "completed"

    repo = gc.get(container_href)
    latest_version_href = repo["latest_version_href"]

    # Check the image is signed on the latest version
    latest_version = gc.get(latest_version_href)
    assert latest_version["content_summary"]["added"]["container.signature"]["count"] > 0

    ee = get_container(gc, "alpine")
    # Check the sign state is set on the UI API
    assert ee["pulp"]["repository"]["sign_state"] == "signed"


@pytest.mark.parametrize(
    "require_auth",
    [
        True,
        False,
    ],
)
@pytest.mark.deployment_standalone
@pytest.mark.skip_in_gw
def test_push_and_sign_a_container(ansible_config, flags, require_auth, galaxy_client):
    can_sign = flags.get("container_signing")
    if not can_sign:
        pytest.skip("GALAXY_CONTAINER_SIGNING_SERVICE is not configured")

    config = ansible_config("admin")
    container_engine = config["container_engine"]
    container_registry = config["container_registry"]

    # Pull alpine image
    pull_and_tag_test_image(container_engine, container_registry)

    # Login to local registry with tls verify disabled
    cmd = [container_engine, "login", "-u", f"{config['username']}", "-p",
           f"{config['password']}", container_registry]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Push image to local registry
    cmd = [container_engine, "push", f"{container_registry}/alpine:latest"]
    if container_engine == 'podman':
        cmd.append("--tls-verify=false")
    subprocess.check_call(cmd)

    # Get an API client running with admin user credentials
    client = get_client(
        config=ansible_config("admin"),
        request_token=True,
        require_auth=require_auth
    )
    api_prefix = client.config.get("api_prefix").rstrip("/")

    # Get the pulp_href for the pushed image
    image = client(
        f"{api_prefix}/pulp/api/v3/repositories/container/container-push/?name=alpine"
    )
    container_href = image["results"][0]["pulp_href"]

    # Get the pulp_href for signing service
    signing_service = client(
        f"{api_prefix}/pulp/api/v3/signing-services/?name=container-default"
    )
    ss_href = signing_service["results"][0]["pulp_href"]

    # Sign the image
    client(f"{container_href}/sign/", method="POST",
           args={"manifest_signing_service": ss_href})

    # sleep 2 second2
    time.sleep(SLEEP_SECONDS_ONETIME)

    repo = client(container_href)
    latest_version_href = repo["latest_version_href"]

    # Check the image is signed on the latest version
    latest_version = client(latest_version_href)
    assert latest_version["content_summary"]["added"]["container.signature"]["count"] > 0

    gc = galaxy_client("admin")
    ee = get_container(gc, "alpine")
    # Check the sign state is set on the UI API
    assert ee["pulp"]["repository"]["sign_state"] == "signed"
