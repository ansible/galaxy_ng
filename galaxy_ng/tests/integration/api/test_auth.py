"""test_auth.py - Test related to authentication.

See: https://github.com/ansible/galaxy-dev/issues/149

"""
import pytest
from ansible.galaxy.api import GalaxyError

from galaxykit.utils import GalaxyClientError
from ..utils import get_client
from ..utils import uuid4

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.parametrize("profile", ("basic_user", "partner_engineer", "org_admin", "admin"))
@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
def test_token_auth(profile, galaxy_client):
    """Test whether normal auth is required and works to access APIs.

    Also tests the settings for user profiles used for testing.
    """
    gc = galaxy_client(profile)
    del gc.headers["Authorization"]
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/")
    assert ctx.value.response.status_code == 403
    gc = galaxy_client(profile, ignore_cache=True)
    resp = gc.get("")
    assert "available_versions" in resp


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
def test_auth_admin(galaxy_client):
    """Test whether admin can not access collections page using invalid token."""

    gc = galaxy_client("admin")
    gc.headers["Authorization"] = f"Bearer {uuid4()}"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/")
    assert ctx.value.response.status_code == 403


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
def test_auth_exception(galaxy_client):
    """Test whether an HTTP exception when using an invalid token."""

    gc = galaxy_client("basic_user")
    gc.headers["Authorization"] = f"Bearer {uuid4()}"
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/")
    assert ctx.value.response.status_code == 403
