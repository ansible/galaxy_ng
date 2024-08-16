import json

import pytest

from galaxykit.client import GalaxyClient


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.parametrize("user_payload", [{"email": "foobar@foobar.com"}, {}])
def test_ui_v2_user_create(
    settings,
    galaxy_client,
    random_username,
    user_payload,
):
    """Test user creation in ui/v2/users/."""

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="this only works local resource management enabled")

    gc = galaxy_client("admin", ignore_cache=True)

    user_payload.update({
        "username": random_username,
        "first_name": "jim",
        "last_name": "bob",
        "password": "redhat1234"
    })

    # create the user in ui/v2 ...
    resp = gc.post(
        "_ui/v2/users/",
        body=json.dumps(user_payload)
    )

    # validate fields ...
    assert resp["username"] == random_username
    assert "password" not in resp
    assert resp["first_name"] == "jim"
    assert resp["last_name"] == "bob"
    assert resp["email"] == user_payload.get("email", "")
    assert resp["resource"]["ansible_id"] is not None

    # validate login ...
    auth = {'username': random_username, 'password': 'redhat1234'}
    ugc = GalaxyClient(gc.galaxy_root, auth=auth)
    me_ds = ugc.get('_ui/v1/me/')
    assert me_ds["username"] == random_username


@pytest.mark.deployment_standalone
def test_ui_v2_user_edit(
    settings,
    galaxy_client,
    random_username,
):
    """Test user edit in ui/v2/users/."""

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="this only works local resource management enabled")

    gc = galaxy_client("admin", ignore_cache=True)

    user_payload = {
        "username": random_username,
        "first_name": "jim",
        "last_name": "bob",
        "password": "redhat1234"
    }

    # create the user in ui/v2 ...
    user_data = gc.post(
        "_ui/v2/users/",
        body=json.dumps(user_payload)
    )
    uid = user_data['id']

    # validate PUT/edit ...
    user_data['last_name'] = 'newname'
    changed_data = gc.put(
        f"_ui/v2/users/{uid}/",
        body=json.dumps(user_data)
    )
    assert changed_data == user_data

    # validate login ...
    auth = {'username': random_username, 'password': 'redhat1234'}
    ugc = GalaxyClient(gc.galaxy_root, auth=auth)
    me_ds = ugc.get('_ui/v1/me/')
    assert me_ds["username"] == random_username
