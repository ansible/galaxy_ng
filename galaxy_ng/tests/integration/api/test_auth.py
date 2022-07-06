"""test_auth.py - Test related to authentication.

See: https://github.com/ansible/galaxy-dev/issues/149

"""
import pytest
from ansible.galaxy.api import GalaxyError

from ..utils import get_client
from ..utils import uuid4

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.parametrize("profile", ("basic_user", "partner_engineer", "org_admin", "admin"))
@pytest.mark.standalone_only
@pytest.mark.galaxyapi_smoke
def test_token_auth(profile, ansible_config):
    """Test whether normal auth is required and works to access APIs.

    Also tests the settings for user profiles used for testing.
    """

    config = ansible_config(profile)

    client = get_client(config, request_token=False, require_auth=False)
    with pytest.raises(GalaxyError) as ctx:
        client("v3/collections/", method="GET")
    assert ctx.value.http_code == 403

    client = get_client(config, request_token=True)
    resp = client("", method="GET")
    assert "available_versions" in resp


@pytest.mark.standalone_only
@pytest.mark.galaxyapi_smoke
def test_auth_admin(ansible_config):
    """Test whether admin can not access API root using invalid token."""

    config = ansible_config("admin")
    client = get_client(
        config,
        request_token=False,
        headers={"Authorization": f"Bearer {uuid4()}"}
    )
    with pytest.raises(GalaxyError) as ctx:
        # url not provided defaults to API root.
        client("", method="GET")
    assert ctx.value.http_code == 403


@pytest.mark.standalone_only
@pytest.mark.galaxyapi_smoke
def test_auth_exception(ansible_config, published):
    """Test whether an HTTP exception when using an invalid token."""

    config = ansible_config("basic_user")
    client = get_client(
        config,
        request_token=False,
        headers={"Authorization": f"Bearer {uuid4()}"}
    )
    with pytest.raises(GalaxyError) as ctx:
        client("", method="GET")
    assert ctx.value.http_code == 403
