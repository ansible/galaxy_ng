"""Tests related to container signing.

See: https://issues.redhat.com/browse/AAH-1358
"""
import subprocess
import time

import pytest

from galaxy_ng.tests.integration.utils import get_client


@pytest.mark.ldap
@pytest.mark.standalone_only
def test_push_container_as_ldap_user(ansible_config):

    # Pull alpine image
    subprocess.check_call(["docker", "pull", "alpine"])
    # Tag the image
    subprocess.check_call(["docker", "tag", "alpine", "localhost:5001/alpine:latest"])

    # get an ldap user
    config = ansible_config("ldap")
    username = config.get('username')
    password = config.get('password')

    # Login to local registy with tls verify disabled
    subprocess.check_call(["docker", "login", "-u", username, "-p", password, "localhost:5001"])

    # Push image to local registry
    pid = subprocess.run(["docker", "push", "localhost:5001/alpine:latest"], stderr=subprocess.PIPE)
    assert pid.returncode == 0, pid.stderr

    '''
    # Get an API client running with admin user credentials
    client = get_client(config=ansible_config("admin"), request_token=True, require_auth=True)

    # Get the pulp_href for the pushed image
    image = client(
        "/api/automation-hub/pulp/api/v3/repositories/container/container-push/?name=alpine"
    )
    container_href = image["results"][0]["pulp_href"]

    # fetch the container
    repo = client(container_href)
    latest_version_href = repo["latest_version_href"]

    # Check the image is signed on the latest version
    latest_version = client(latest_version_href)
    # assert latest_version["content_summary"]["added"]["container.signature"]["count"] > 0
    import epdb; epdb.st()

    # Check the sign state is set on the UI API
    ee = client("/api/automation-hub/_ui/v1/execution-environments/repositories/?name=alpine")
    # assert ee["data"][0]["pulp"]["repository"]["sign_state"] == "signed"
    import epdb; epdb.st()
    '''
