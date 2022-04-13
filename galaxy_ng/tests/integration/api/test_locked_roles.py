"""test_locked_roles.py - Tests creation of locked roles."""

import pytest

from ..utils import get_client

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.standalone_only
@pytest.mark.role
def test_locked_roles_exist(ansible_config):
    galaxy_locked_roles = [
        "galaxy.collection_admin",
        "galaxy.execution_environment_admin",
        "galaxy.group_admin",
        "galaxy.publisher",
        "galaxy.user_admin",
        "galaxy.namespace_owner",
        "galaxy.synclist_owner",
        "galaxy.content_admin"
    ]

    config = ansible_config("ansible_partner")
    api_client = get_client(
        config=config,
        require_auth=True,
        request_token=False
    )
    resp = api_client('/pulp/api/v3/roles/', method='GET')
    locked_roles = resp['results']

    galaxy_locked_roles_count = 0
    for role in locked_roles:
        if role["name"].startswith("galaxy.") and role["locked"]:
            galaxy_locked_roles_count += 1
            assert role["name"] in galaxy_locked_roles and role["locked"]
    assert len(galaxy_locked_roles) == galaxy_locked_roles_count
