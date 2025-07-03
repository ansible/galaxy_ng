import json

import pytest

from galaxykit.client import BasicAuthClient
from galaxykit.utils import GalaxyClientError

from ..utils.namespaces import generate_namespace


@pytest.mark.deployment_standalone
def test_ui_v2_teams(galaxy_client):

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, "admin", "admin")

    # make the team via the _ui/v2/teams/ endpoint
    random_name = generate_namespace()
    team_data = ga.post(
        "/api/galaxy/_ui/v2/teams/",
        body=json.dumps({"name": random_name})
    )

    assert random_name == team_data["name"]

    # update the team via the _ui/v2/teams/ endpoint
    random_name2 = generate_namespace()
    team_update_data = ga.patch(
        f"/api/galaxy/_ui/v2/teams/{team_data['id']}/",
        body=json.dumps({"name": random_name2})
    )

    assert random_name2 == team_update_data["name"]

    # delete the team via the _ui/v2/teams/ endpoint
    with pytest.raises(GalaxyClientError) as exc_info:
        team_update_data = ga.delete(
            f"/api/galaxy/_ui/v2/teams/{team_update_data['id']}/"
        )

    print(f"exc_info:\n{str(exc_info)}")

    assert "204" in str(exc_info)
