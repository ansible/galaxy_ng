import pytest

from ..utils.iqe_utils import remove_from_cache


@pytest.mark.min_hub_version("4.10")
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
    assert "pulp-v3" not in response["available_versions"]
    # verify version info is not disclosed to unauthenticated users (AAP-68691)
    assert "server_version" not in response
    assert "galaxy_ng_version" not in response
    assert "galaxy_ng_commit" not in response
    assert "galaxy_importer_version" not in response
    assert "pulp_core_version" not in response
    assert "pulp_ansible_version" not in response
    assert "pulp_container_version" not in response
    assert "ansible_base_version" not in response
    assert "ansible_lint_version" not in response
    assert "dynaconf_version" not in response
    assert "django_version" not in response
    assert "aap_version" not in response


@pytest.mark.min_hub_version("4.10")
@pytest.mark.deployment_standalone
@pytest.mark.skip_in_gw
def test_galaxy_api_root_standalone_auth_has_versions(galaxy_client):
    """Test that authenticated users can see version info."""

    gc = galaxy_client("basic_user")
    response = gc.get("")
    assert "available_versions" in response
    assert "server_version" in response
    assert "galaxy_ng_version" in response
    assert "pulp_core_version" in response
    assert "pulp_ansible_version" in response
    assert "pulp_container_version" in response


@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_galaxy_api_root(galaxy_client, artifact):
    """Test galaxy API root."""

    # TODO(chr-stian): change to `basic_user` profile when can access pulp-v3 api root
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

    # TODO(chr-stian): change to `basic_user` profile when can access pulp-v3 api root
    gc = galaxy_client("admin")

    # verify api root works
    response = gc.get(gc.galaxy_root)
    assert "v3" in response["available_versions"]

    v3_root = gc.get(response['available_versions']['v3'])
    assert "published" in v3_root
