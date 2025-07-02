import json
import os
import uuid

import pytest


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.skipif(
    os.getenv("ENABLE_DAB_TESTS"),
    reason="Skipping test because ENABLE_DAB_TESTS is set"
)
@pytest.mark.skip_in_gw
def test_system_auditor_role_permissions_without_gateway(galaxy_client):
    """Tests the galaxy.system_auditor role can be added to a user and has the right perms."""

    gc = galaxy_client("admin", ignore_cache=True)

    # make a random user
    username = str(uuid.uuid4())
    uinfo = gc.post(
        "_ui/v1/users/",
        body=json.dumps({"username": username, "password": "redhat1234"})
    )
    uid = uinfo["id"]

    # assign the galaxy.system_auditor role to the user
    rinfo = gc.post(
        f"pulp/api/v3/users/{uid}/roles/",
        body=json.dumps({'content_object': None, 'role': 'galaxy.auditor'})
    )

    # check that all the permissions are view_* only ...
    for perm_code in rinfo["permissions"]:
        perm_name = perm_code.split(".", 1)[1]
        assert "view_" in perm_name, f"{perm_code} is not a view-only permission"
