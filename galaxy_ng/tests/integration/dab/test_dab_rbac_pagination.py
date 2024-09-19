import pytest


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10")
def test_dab_rbac_pagination(galaxy_client):
    gc = galaxy_client("admin", ignore_cache=True)
    roledefs = gc.get('_ui/v2/role_definitions/?page_size=1')
    assert len(roledefs['results']) == 1
