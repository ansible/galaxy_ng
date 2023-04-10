"""Tests related to container signing.

See: https://issues.redhat.com/browse/AAH-1358
"""
import subprocess
from urllib.parse import urlparse

import pytest

from galaxy_ng.tests.integration.utils import (
    get_client,
    ensure_test_container_is_pulled,
    tag_hub_with_registry
)


@pytest.fixture(scope="function")
def settings(ansible_config):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=False, require_auth=True)
    return api_client(f"{api_prefix}/_ui/v1/settings/")





# TODO: make add ldap credentials to conftest
@pytest.mark.private_hub
def test_push_container_as_ldap_user(ansible_config, settings):

    if not settings.get("GALAXY_AUTH_LDAP_ENABLED"):
        pytest.skip("GALAXY_AUTH_LDAP_ENABLED is not enabled")

    # get an ldap user
    config = ansible_config("ldap")
    username = config.get('username')
    password = config.get('password')

    # make sure django mapped the correct user
    client = get_client(config)
    this_user = client('_ui/v1/me/')
    assert this_user['username'] == username

    # Pull alpine image
    ensure_test_container_is_pulled(container="alpine")
    # Tag the image
    img = tag_hub_with_registry(config, "alpine", "alpine1:latest")

    # Push image to local registry
    pid = subprocess.run(
        [
            "podman",
            "--debug",
            "push",
            "--creds",
            f"{username}:{password}",
            img,
            "--tls-verify=false"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )

    assert pid.returncode == 0, pid.stdout
