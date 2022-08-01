"""test_locked_roles.py - Tests creation of locked roles."""

import pytest

from ..utils import get_client

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.standalone_only
@pytest.mark.role
def test_locked_roles_exist(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        require_auth=True,
        request_token=False
    )
    resp = api_client('/pulp/api/v3/roles/?name__startswith=galaxy.', method='GET')

    # verify that the locked roles are getting populated
    assert resp["count"] > 0
