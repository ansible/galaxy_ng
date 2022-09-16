"""Tests related to container signing.

See: https://issues.redhat.com/browse/AAH-1358
"""
import subprocess
from urllib.parse import urlparse

import pytest

from galaxy_ng.tests.integration.utils import get_client


@pytest.fixture(scope="function")
def settings(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(config, request_token=False, require_auth=True)
    return api_client("/api/automation-hub/_ui/v1/settings/")


@pytest.mark.ldap
@pytest.mark.standalone_only
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

    # get the host:port from the config
    url = config.get('url')
    o = urlparse(url)
    registry = o.netloc

    # Pull alpine image
    subprocess.check_call(["docker", "pull", "alpine"])

    # Tag the image
    subprocess.check_call(["docker", "tag", "alpine", f"{registry}/alpine:latest"])

    # Login to local registy with tls verify disabled
    subprocess.check_call(["docker", "login", "-u", username, "-p", password, registry])

    # Push image to local registry
    pid = subprocess.run(
        ["docker", "--debug", "push", f"{registry}/alpine:latest"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout
