import pytest

from ..utils import get_client
from ..utils.iqe_utils import remove_from_cache


@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_galaxy_api_root(ansible_config, artifact):
    """Test galaxy API root."""

    # TODO: change to `basic_user` profile when can access pulp-v3 api root
    config = ansible_config("admin")

    api_prefix = config.get("api_prefix")
    api_prefix = api_prefix.rstrip("/")

    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # verify api root works
    response = api_client(api_prefix + '/')
    assert "v3" in response["available_versions"]
    assert "pulp-v3" in response["available_versions"]

    v3_root = api_client(api_prefix + '/' + response['available_versions']['v3'])
    assert "published" in v3_root

    pulp_root = api_client(api_prefix + '/' + response['available_versions']['pulp-v3'])
    assert "tasks" in pulp_root


@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.deployment_standalone
def test_galaxy_api_root_standalone_no_auth_access(galaxy_client):
    """Test galaxy API root."""
    # TODO: change to `basic_user` profile when can access pulp-v3 api root
    gc = galaxy_client("admin")
    del gc.headers["Authorization"]
    remove_from_cache("admin")
    # verify api root works without authentication
    response = gc.get("")
    assert "v3" in response["available_versions"]
    assert "pulp-v3" in response["available_versions"]


@pytest.mark.max_hub_version("4.5.5")
@pytest.mark.all
def test_galaxy_api_root_v_4_5(ansible_config, artifact):
    """Test galaxy API root."""

    # TODO: change to `basic_user` profile when can access pulp-v3 api root
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix")
    api_prefix = api_prefix.rstrip("/")

    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # verify api root works
    response = api_client(api_prefix + '/')
    assert "v3" in response["available_versions"]

    v3_root = api_client(api_prefix + '/' + response['available_versions']['v3'])
    assert "published" in v3_root
