"""test_auth.py - Test related to authentication.

See: https://github.com/ansible/galaxy-dev/issues/149

"""
import pytest

from galaxykit.utils import GalaxyClientError
from urllib.parse import urlparse
from ..utils import uuid4
from ..utils.iqe_utils import is_keycloak
from ..utils.iqe_utils import remove_from_cache, aap_gateway

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.parametrize("profile", ("basic_user", "partner_engineer", "org_admin", "admin"))
@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
@pytest.mark.skip_in_gw
def test_token_auth(profile, galaxy_client):
    """Test whether normal auth is required and works to access APIs.

    Also tests the settings for user profiles used for testing.
    """
    gc = galaxy_client(profile)
    del gc.headers["Authorization"]
    remove_from_cache(profile)

    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/")
    assert ctx.value.response.status_code == 401
    gc = galaxy_client(profile, ignore_cache=True)
    resp = gc.get("")
    assert "available_versions" in resp


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
@pytest.mark.skip_in_gw
def test_auth_admin(galaxy_client):
    """Test whether admin can not access collections page using invalid token."""

    gc = galaxy_client("admin")
    gc.headers["Authorization"] = f"Bearer {uuid4()}"
    remove_from_cache("admin")
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/")
    assert ctx.value.response.status_code == 401


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
@pytest.mark.skip_in_gw
def test_auth_exception(galaxy_client):
    """Test whether an HTTP exception when using an invalid token."""

    gc = galaxy_client("basic_user")
    gc.headers["Authorization"] = f"Bearer {uuid4()}"
    remove_from_cache("basic_user")
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/collections/")
    assert ctx.value.response.status_code == 401


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gateway_auth_admin_gateway_sessionid(galaxy_client):
    """Test whether admin can not access collections page using invalid gateway_sessionid."""
    gc = galaxy_client("admin")
    alt_cookies = gc.gw_client.cookies
    alt_cookies["gateway_sessionid"] = uuid4()
    gc.headers["Cookie"] = (f"csrftoken={alt_cookies['csrftoken']}; "
                            f"gateway_sessionid={alt_cookies['gateway_sessionid']}")
    remove_from_cache("admin")
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/plugin/ansible/content/published/collections/index/", relogin=False)
    assert ctx.value.response.status_code == 403
    remove_from_cache("admin")


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gateway_auth_admin_gateway_csrftoken(galaxy_client):
    """Test whether admin can not access collections page using invalid csrftoken."""
    # TODO: This test fails, invalid csrftoken does not return 403. Is it correct?
    gc = galaxy_client("admin")
    alt_cookies = gc.gw_client.cookies
    alt_cookies["csrftoken"] = uuid4()
    gc.headers["Cookie"] = (f"csrftoken={alt_cookies['csrftoken']};"
                            f" gateway_sessionid={alt_cookies['gateway_sessionid']}")
    remove_from_cache("admin")
    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/plugin/ansible/content/published/collections/index/", relogin=False)
    assert ctx.value.response.status_code == 403
    remove_from_cache("admin")


@pytest.mark.deployment_standalone
@pytest.mark.galaxyapi_smoke
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gateway_token_auth(galaxy_client):
    """Test whether normal auth is required and works to access APIs.

    Also tests the settings for user profiles used for testing.
    """
    gc = galaxy_client("admin")
    del gc.headers["Cookie"]
    remove_from_cache("admin")

    with pytest.raises(GalaxyClientError) as ctx:
        gc.get("v3/plugin/ansible/content/published/collections/index/", relogin=False)
    assert ctx.value.response.status_code == 403


@pytest.mark.deployment_standalone
@pytest.mark.skip_in_gw
def test_ui_login_csrftoken(galaxy_client):
    if is_keycloak():
        pytest.skip("This test is not valid for keycloak")
    gc = galaxy_client("admin")
    r = gc.get("_ui/v1/auth/login/", parse_json=False)
    csrftoken = r.cookies.get("csrftoken")

    parsed_url = urlparse(gc.galaxy_root)
    url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    headers = {
        "Cookie": f"csrftoken={csrftoken}",
        "Origin": url,
        "Referer": f"{url}/ui/login/?next=%2F",
        "X-Csrftoken": csrftoken
    }
    body = {
        "username": gc.username,
        "password": gc.password
    }
    r = gc.post("_ui/v1/auth/login/", body=body, headers=headers, parse_json=False)
    assert r.cookies.get("sessionid")
