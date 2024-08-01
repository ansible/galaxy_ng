"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
import random
import string
import uuid
import os

import pytest
from requests import HTTPError

from galaxykit.groups import create_group_v3, create_group, get_roles, \
    delete_group_v3, get_group_v3
from galaxykit.namespaces import create_namespace
from ..utils import UIClient, get_client
from ..utils.iqe_utils import aap_gateway

from ..utils.iqe_utils import AnsibleConfigFixture

pytestmark = pytest.mark.qa  # noqa: F821
CLIENT_CONFIG = AnsibleConfigFixture("admin")
API_PREFIX = CLIENT_CONFIG.get("api_prefix").rstrip("/")


@pytest.mark.parametrize(
    'test_data',
    [
        {"url": "_ui/v1/groups/"},
        {"url": "pulp/api/v3/groups/"},
    ]
)
@pytest.mark.group
@pytest.mark.role
@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skipif(
    os.getenv("ENABLE_DAB_TESTS"),
    reason="Group creation is disabled in the DAB test profile."
)
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gw_group_role_listing(galaxy_client, test_data):
    """Tests ability to list roles assigned to a namespace."""

    gc = galaxy_client("admin", ignore_cache=True)
    # Create Group
    group_name = str(uuid.uuid4())

    if "v3" in test_data["url"]:
        group_response = create_group_v3(gc, group_name)
    if "v1" in test_data["url"]:
        group_response = create_group(gc, group_name)

    assert group_response["name"] == group_name

    # Create Namespace
    ns_name = "".join(random.choices(string.ascii_lowercase, k=10))
    object_roles = ["galaxy.collection_namespace_owner"]
    ns_response = create_namespace(gc, ns_name, group_name, object_roles)
    assert ns_response["name"] == ns_name
    assert ns_response["groups"][0]["name"] == group_response["name"]

    # List Group's Roles
    group_roles_response = get_roles(gc, group_name)
    assert group_roles_response["count"] == 1
    assert group_roles_response["results"][0]["role"] == "galaxy.collection_namespace_owner"
    assert f'/groups/{group_response["id"]}/' in group_roles_response["results"][0]["pulp_href"]

    delete_group_v3(gc, group_name)
    with pytest.raises(ValueError):
        get_group_v3(gc, group_name)


@pytest.mark.parametrize(
    'test_data',
    [
        {"url": f"{API_PREFIX}/_ui/v1/groups/", "require_auth": True},
        {"url": f"{API_PREFIX}/_ui/v1/groups/", "require_auth": False},
        {"url": f"{API_PREFIX}/pulp/api/v3/groups/", "require_auth": True},
        {"url": f"{API_PREFIX}/pulp/api/v3/groups/", "require_auth": False},
    ]
)
@pytest.mark.group
@pytest.mark.role
@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.skip_in_gw
def test_group_role_listing(ansible_config, test_data):
    """Tests ability to list roles assigned to a namespace."""

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=True, require_auth=test_data["require_auth"])

    # Create Group
    group_name = str(uuid.uuid4())
    payload = {"name": group_name}
    group_response = api_client(test_data["url"], args=payload, method="POST")
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
    ns_response = api_client(f"{api_prefix}/v3/namespaces/", args=payload, method="POST")
    assert ns_response["name"] == ns_name
    assert ns_response["groups"][0]["name"] == group_response["name"]

    # List Group's Roles
    group_roles_response = api_client(
        f'/pulp/api/v3/groups/{group_response["id"]}/roles/', method="GET"
    )
    assert group_roles_response["count"] == 1
    assert group_roles_response["results"][0]["role"] == "galaxy.collection_namespace_owner"
    assert f'/groups/{group_response["id"]}/' in group_roles_response["results"][0]["pulp_href"]

    #  Delete Group
    with UIClient(config=config) as uclient:
        del_group_resp = uclient.delete(f'pulp/api/v3/groups/{group_response["id"]}/')
        assert del_group_resp.status_code == 204

        with pytest.raises(HTTPError) as ctx:
            uclient.get(f'pulp/api/v3/groups/{group_response["id"]}/')
        assert ctx.value.strerror.status_code == 404
