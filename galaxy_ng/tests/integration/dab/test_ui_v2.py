import copy
import json
from http import HTTPStatus

import pytest

from galaxykit.client import GalaxyClient
from galaxykit.utils import GalaxyClientError

from galaxy_ng.tests.integration.utils.tools import random_name


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.parametrize("user_payload", [
    {},
    {"email": "foobar@foobar.com"},
    {"password": None},
])
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
        # "password": "redhat1234"
    })
    if "password" not in user_payload:
        user_payload["password"] = "redhat1234"

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

    # validate login if a password was created...
    if user_payload["password"] is not None:
        auth = {'username': random_username, 'password': 'redhat1234'}
        ugc = GalaxyClient(gc.galaxy_root, auth=auth)
        me_ds = ugc.get('_ui/v1/me/')
        assert me_ds["username"] == random_username


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.parametrize("invalid_payload", [
    ({"email": "invalidemail"}, "Enter a valid email address."),
    ({"email": "@whoops"}, "Enter a valid email address."),
    ({"username": ""}, "This field may not be blank"),
    ({"password": "short"}, "This password is too short"),
    ({"password": ""}, "This field may not be blank"),
])
def test_ui_v2_user_create_invalid_data(
    settings,
    galaxy_client,
    invalid_payload,
    random_username,
):
    """Test user edits in ui/v2/users/ with invalid data."""

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="this only works local resource management enabled")

    gc = galaxy_client("admin", ignore_cache=True)

    invalid_payload[0].update({
        "first_name": "jim",
        "last_name": "bob",
    })
    if 'username' not in invalid_payload[0]:
        invalid_payload[0]['username'] = random_username

    exc = None
    try:
        gc.post(
            "_ui/v2/users/",
            body=json.dumps(invalid_payload[0]),
        )
    except Exception as e:
        exc = e

    assert exc.response.status_code == 400
    assert invalid_payload[1] in exc.response.text


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
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


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.parametrize("invalid_payload", [
    ({"email": "invalidemail"}, "Enter a valid email address."),
    ({"email": "@whoops"}, "Enter a valid email address."),
    ({"username": ""}, "This field may not be blank"),
    ({"password": "short"}, "This password is too short"),
    ({"password": ""}, "This field may not be blank"),
    ({"groups": [{"name": "HITHERE"}]}, "does not exist"),
    ({"teams": [{"name": "HITHERE"}]}, "does not exist"),
    ({"organizations": [{"name": "HITHERE"}]}, "does not exist"),
])
def test_ui_v2_user_edit_invalid_data(
    settings,
    galaxy_client,
    invalid_payload,
    random_username,
):
    """Test user edits in ui/v2/users/ with invalid data."""

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

    new_payload = copy.deepcopy(user_data)
    new_payload.update(invalid_payload[0])

    exc = None
    try:
        gc.put(
            f"_ui/v2/users/{uid}/",
            body=json.dumps(new_payload)
        )
    except Exception as e:
        exc = e

    assert exc.response.status_code == 400
    assert invalid_payload[1] in exc.response.text


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_ui_v2_teams(
    settings,
    galaxy_client,
    random_username,
):
    """Test teams creation and deletion."""

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="this only works local resource management enabled")

    client = galaxy_client("admin", ignore_cache=True)

    # Create a team
    team_name = random_name('team')
    team = client.post('_ui/v2/teams/', body={"name": team_name})
    assert team["name"] == team_name

    # Check that team exists
    team = client.get(f"_ui/v2/teams/{team['id']}/")
    assert team["name"] == team_name

    # Check that associated group exists
    group = client.get(f"_ui/v1/groups/{team['group']['id']}/")
    assert group["id"] == team["group"]["id"]
    assert group["name"] == f"Default::{team_name}"

    # Delete a team
    response = client.delete(f"_ui/v2/teams/{team['id']}/", parse_json=False)
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Check that team does not exist
    with pytest.raises(GalaxyClientError) as ctx:
        client.get(f"_ui/v2/teams/{team['id']}/")
    assert ctx.value.response.status_code == HTTPStatus.NOT_FOUND

    # Check that associated group does not exist
    with pytest.raises(GalaxyClientError) as ctx:
        client.get(f"_ui/v1/groups/{team['group']['id']}/")
    assert ctx.value.response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_ui_v2_teams_membership_local_and_nonlocal(
    settings,
    galaxy_client,
    random_username,
):
    """Test teams creation and deletion."""

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip(reason="this only works local resource management enabled")

    org_name = random_username.replace('user_', 'org_')
    team1_name = random_username.replace('user_', 'team1_')
    team2_name = random_username.replace('user_', 'team2_')

    client = galaxy_client("admin", ignore_cache=True)

    # make the org
    client.post(
        '_ui/v2/organizations/',
        body={'name': org_name}
    )

    # make the 1st team
    team1_data = client.post(
        '_ui/v2/teams/',
        body={'name': team1_name, 'organization': org_name}
    )

    # make the 2nd team
    team2_data = client.post(
        '_ui/v2/teams/',
        body={'name': team2_name, 'organization': org_name}
    )

    # make the user
    user_data = client.post(
        '_ui/v2/users/',
        body={'username': random_username, 'password': 'redhat1234'}
    )

    # get all the roledefs ...
    roledefs = client.get('_ui/v2/role_definitions/')
    roledefs = {x['name']: x for x in roledefs['results']}

    # assign "local" membership on team1
    client.post(
        '_ui/v2/role_user_assignments/',
        body={
            'user': user_data['id'],
            'role_definition': roledefs['Team Member']['id'],
            'object_id': team1_data['id'],
        }
    )

    # assign !local? membership on team2
    client.post(
        '_ui/v2/role_user_assignments/',
        body={
            'user': user_data['id'],
            'role_definition': roledefs['Team Member']['id'],
            'object_id': team2_data['id'],
        }
    )

    # check that the user's serialized data shows both teams ...
    new_user_data = client.get(f'_ui/v2/users/?username={random_username}')
    new_user_data = new_user_data['results'][0]
    member_teams = [x['name'] for x in new_user_data['teams']]
    assert len(member_teams) == 2
    assert sorted(member_teams) == sorted([team1_name, team2_name])
