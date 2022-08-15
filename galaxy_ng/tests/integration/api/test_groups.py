"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
import random
import string
import uuid

import pytest

from ..utils import get_client

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.group
@pytest.mark.role
@pytest.mark.standalone_only
def test_group_role_listing(ansible_config):
    """Tests ability to list roles assigned to a namespace."""

    config = ansible_config("admin")
    api_client = get_client(config, request_token=True, require_auth=True)

    # Create Group
    group_name = str(uuid.uuid4())
    payload = {"name": group_name}
    group_response = api_client("/api/automation-hub/_ui/v1/groups/", args=payload, method="POST")
    assert group_response["name"] == group_name

    # Create Namespace
    ns_name = "".join(random.choices(string.ascii_lowercase, k=10))
    payload = {
        "name": ns_name,
        "groups": [
            {
                "name": f"{group_response['name']}",
                "object_roles": ["galaxy.collection_namespace_owner"],
            }
        ],
    }
    ns_response = api_client("/api/automation-hub/v3/namespaces/", args=payload, method="POST")
    assert ns_response["name"] == ns_name
    assert ns_response["groups"][0]["name"] == group_response["name"]

    # List Group's Roles
    group_roles_response = api_client(
        f'/pulp/api/v3/groups/{group_response["id"]}/roles/', method="GET"
    )
    assert group_roles_response["count"] == 1
    assert group_roles_response["results"][0]["role"] == "galaxy.collection_namespace_owner"
    assert f'/groups/{group_response["id"]}/' in group_roles_response["results"][0]["pulp_href"]
