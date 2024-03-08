"""test_locked_roles.py - Tests creation of locked roles."""

import pytest

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.role
@pytest.mark.min_hub_version("4.6dev")
def test_locked_roles_exist(galaxy_client):
    gc = galaxy_client("admin")
    resp = gc.get('pulp/api/v3/roles/?name__startswith=galaxy.')
    # verify that the locked roles are getting populated
    assert resp["count"] > 0
