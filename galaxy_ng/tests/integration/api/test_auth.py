"""test_auth.py - Test related to authentication.

See: https://github.com/ansible/galaxy-dev/issues/149

"""
import pytest
from ansible.galaxy.api import GalaxyError

from ..utils import get_client
from ..utils import uuid4

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.skip(reason="fails in ephemeral")
@pytest.mark.parametrize("user", ("ansible_user", "ansible_partner", "ansible_insights"))
@pytest.mark.galaxyapi_smoke
def test_token_auth(user, ansible_config):
    """Test whether normal auth is required and works to access APIs.

    Also tests the settings for all three roles used for testing.
    """

    config = ansible_config("ansible_partner")

    client = get_client(config, request_token=False, require_auth=False)
    with pytest.raises(GalaxyError) as ctx:
        client("v3/collections/", method="GET")
    assert ctx.value.http_code == 403

    client = get_client(config, request_token=True)
    resp = client("", method="GET")
    assert "available_versions" in resp


@pytest.mark.skip(reason="fails in ephemeral")
@pytest.mark.galaxyapi_smoke
def test_auth_admin(ansible_config):
    """Test whether admin can not access API root using invalid token."""

    config = ansible_config("ansible_insights")
    client = get_client(
        config,
        request_token=False,
        headers={"Authorization": f"Bearer {uuid4()}"}
    )
    with pytest.raises(GalaxyError) as ctx:
        # url not provided defaults to API root.
        client("", method="GET")
    assert ctx.value.http_code == 403


@pytest.mark.skip(reason="fails in ephemeral")
@pytest.mark.galaxyapi_smoke
def test_auth_exception(ansible_config, published):
    """Test whether an HTTP exception when using an invalid token."""

    config = ansible_config("ansible_insights")
    client = get_client(
        config,
        request_token=False,
        headers={"Authorization": f"Bearer {uuid4()}"}
    )
    with pytest.raises(GalaxyError) as ctx:
        client("", method="GET")
    assert ctx.value.http_code == 403
