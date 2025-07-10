import json

import pytest

from galaxykit.client import BasicAuthClient
from galaxykit.utils import GalaxyClientError

from ..utils.namespaces import generate_namespace


@pytest.mark.parametrize("endpoint", ["groups", "teams"])
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0dev")
def test_ui_v2_teams(galaxy_client, endpoint, settings):
    """
    Test creating, updating, and deleting a team or group
    via the _ui/v2/teams/ or _ui/v2/groups/ endpoint.
    """
    if settings.get("IS_CONNECTED_TO_RESOURCE_SERVER"):
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # make the team via the _ui/v2/teams/ endpoint
    random_name = generate_namespace()
    endpoint_data = ga.post(
        f"/api/galaxy/_ui/v2/{endpoint}/",
        body=json.dumps({"name": random_name})
    )

    assert random_name == endpoint_data["name"]

    # update the team via the _ui/v2/teams/ endpoint
    random_name2 = generate_namespace()
    endpoint_update_data = ga.patch(
        f"/api/galaxy/_ui/v2/{endpoint}/{endpoint_data['id']}/",
        body=json.dumps({"name": random_name2})
    )

    assert random_name2 == endpoint_update_data["name"]

    # delete the team via the _ui/v2/teams/ endpoint
    with pytest.raises(GalaxyClientError) as exc_info:
        ga.delete(
            f"/api/galaxy/_ui/v2/{endpoint}/{endpoint_update_data['id']}/"
        )

    assert "204" in str(exc_info)
