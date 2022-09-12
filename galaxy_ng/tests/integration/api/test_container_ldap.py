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
    pid = subprocess.run(
        ["docker", "--debug", "push", "localhost:5001/alpine:latest"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    assert pid.returncode == 0, pid.stdout
