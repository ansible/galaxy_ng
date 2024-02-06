"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
import random
import string
import uuid

import pytest

from galaxykit.groups import create_group_v3, create_group, get_roles, delete_group, \
    delete_group_v3, get_group_v3
from galaxykit.namespaces import create_namespace

from ..utils.iqe_utils import AnsibleConfigFixture, remove_from_cache

pytestmark = pytest.mark.qa  # noqa: F821
CLIENT_CONFIG = AnsibleConfigFixture("admin")
API_PREFIX = CLIENT_CONFIG.get("api_prefix").rstrip("/")


@pytest.mark.parametrize(
    'test_data',
    [
        {"url": "_ui/v1/groups/", "require_auth": True},
        {"url": "_ui/v1/groups/", "require_auth": False},
        {"url": "pulp/api/v3/groups/", "require_auth": True},
        {"url": "pulp/api/v3/groups/", "require_auth": False},
    ]
)
@pytest.mark.group
@pytest.mark.role
@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
def test_group_role_listing(galaxy_client, test_data):
    """Tests ability to list roles assigned to a namespace."""

    gc = galaxy_client("admin", ignore_cache=True)
    if not test_data["require_auth"]:
        gc = galaxy_client("basic_user", ignore_cache=True)
        try:
            del gc.headers["Authorization"]
        except KeyError:
            gc.gw_client.logout()
        remove_from_cache("basic_user")

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
