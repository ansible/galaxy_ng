import json

import pytest

from galaxykit.client import BasicAuthClient
from galaxykit.utils import GalaxyClientError

from ..utils.namespaces import generate_namespace
from ..utils.iqe_utils import is_disabled_local_management


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.11.0")
@pytest.mark.skipif(
    is_disabled_local_management(),
    reason="this test relies on local resource management"
)
def test_ui_v2_user_creation(galaxy_client, settings):
    """Test user creation, update, and deletion via the _ui/v2/users/ endpoint."""
    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # make the user via the _ui/v2/users/ endpoint
    random_name = generate_namespace()
    user_data = ga.post(
        "/api/galaxy/_ui/v2/users/",
        body=json.dumps({
            "username": random_name,
            "password": "redhat1234",
            "first_name": random_name
        })
    )

    assert random_name == user_data["username"]

    # update the user via the _ui/v2/users/ endpoint
    random_name2 = generate_namespace()
    user_update_data = ga.patch(
        f"/api/galaxy/_ui/v2/users/{user_data['id']}/",
        body=json.dumps({"username": random_name, "first_name": random_name2})
    )

    assert random_name == user_update_data["username"]
    assert random_name2 == user_update_data["first_name"]

    # delete the user via the _ui/v2/users/ endpoint
    with pytest.raises(GalaxyClientError) as exc_info:
        user_update_data = ga.delete(
            f"/api/galaxy/_ui/v2/users/{user_update_data['id']}/"
        )

    assert "204" in str(exc_info)


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10.0")
@pytest.mark.skipif(
    is_disabled_local_management(),
    reason="this test relies on local resource management"
)
def test_ui_v2_user_detail_correct_format_display(galaxy_client, settings):
    """Test user creation, update, and deletion via the _ui/v2/users/ endpoint."""
    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

    # make the user via the _ui/v2/users/ endpoint
    random_name = generate_namespace()
    user_data = ga.post(
        "/api/galaxy/_ui/v2/users/",
        body=json.dumps({
            "username": random_name,
            "password": "redhat1234",
            "first_name": random_name
        })
    )

    user_json = ga.get(
        f"/api/galaxy/_ui/v2/users/{user_data['id']}/",
    )

    assert random_name == user_json["username"]

    user_api = ga.get(
        f"/api/galaxy/_ui/v2/users/{user_data['id']}/", parse_json=False
    )

    for field in ("username", "groups", "organizations", "teams"):
        assert field in user_api
    assert random_name in user_api
