import pytest

from ..utils.iqe_utils import remove_from_cache


@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.deployment_standalone
@pytest.mark.skip_in_gw
def test_galaxy_api_root_standalone_no_auth_access(galaxy_client):
    """Test galaxy API root."""

    gc = galaxy_client("basic_user")
    remove_from_cache("basic_user")
    del gc.headers["Authorization"]
    # verify api root works without authentication
    response = gc.get("")
    assert "v3" in response["available_versions"]
    assert "pulp-v3" in response["available_versions"]


@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_galaxy_api_root(galaxy_client, artifact):
    """Test galaxy API root."""

    # TODO: change to `basic_user` profile when can access pulp-v3 api root
    gc = galaxy_client("admin")
    # verify api root works
    response = gc.get(gc.galaxy_root)
    assert "v3" in response["available_versions"]
    assert "pulp-v3" in response["available_versions"]

    # v3_root = gc.get(response['available_versions']['v3'])
    v3_root = gc.get("v3/plugin/ansible/content/published/collections/")
    assert "published" in v3_root

    pulp_root = gc.get(response['available_versions']['pulp-v3'])
    assert "tasks" in pulp_root


@pytest.mark.max_hub_version("4.5.5")
@pytest.mark.all
def test_galaxy_api_root_v_4_5(galaxy_client, artifact):
    """Test galaxy API root."""

    # TODO: change to `basic_user` profile when can access pulp-v3 api root
    gc = galaxy_client("admin")

    # verify api root works
    response = gc.get(gc.galaxy_root)
    assert "v3" in response["available_versions"]

    v3_root = gc.get(response['available_versions']['v3'])
    assert "published" in v3_root
