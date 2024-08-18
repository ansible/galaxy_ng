import json

import pytest

from galaxykit.client import GalaxyClient
from galaxy_ng.tests.integration.utils.namespaces import generate_namespace


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.parametrize("user_payload", [
    {},
    {"email": "foobar@foobar.com"},
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
@pytest.mark.parametrize("user_payload", [
    {"groups": [{"name": "$RANDOM"}]},
    {"teams": [{"name": "$RANDOM", "organization": "$RANDOM"}]},
    {"organizations": [{"name": "$RANDOM"}]},
])
def test_ui_v2_user_create_with_groups_and_teams_and_orgs(
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

    expected_groups = []
    expected_teams = []
    expected_orgs = []

    if user_payload.get("groups"):
        for idg, gdata in enumerate(user_payload["groups"]):
            group_name = 'group_' + generate_namespace()
            user_payload["groups"][idg]["name"] = group_name
            gc.post(
                "_ui/v2/groups/",
                body=json.dumps({"name": group_name})
            )
            expected_groups.append(group_name)

    if user_payload.get("teams"):
        for idt, tdata in enumerate(user_payload["teams"]):
            org_name = 'org_' + generate_namespace()
            team_name = 'team_' + generate_namespace()
            group_name = org_name + '::' + team_name

            # make the org
            gc.post(
                '_ui/v2/organizations/',
                body=json.dumps({"name": org_name})
            )

            # make the team
            gc.post(
                '_ui/v2/teams/',
                body=json.dumps({"name": team_name, "organization": org_name})
            )

            # expected_groups.append(group_name)
            expected_teams.append(team_name)
            # expected_orgs.append(org_name)

            user_payload['teams'][idt]['name'] = team_name
            user_payload['teams'][idt].pop('organization', None)

    if user_payload.get("organizations"):
        for ido, odata in enumerate(user_payload["organizations"]):
            org_name = 'org_' + generate_namespace()

            # make the org
            gc.post(
                '_ui/v2/organizations/',
                body=json.dumps({"name": org_name})
            )

            expected_orgs.append(org_name)

            user_payload['organizations'][ido]['name'] = org_name

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

    # get the full rendered user detail
    # uresp = gc.get(f'_ui/v2/users/?username={random_username}')

    if expected_groups:
        actual_groups = [x['name'] for x in resp['groups']]
        assert sorted(expected_groups) == sorted(actual_groups)

    if expected_teams:
        actual_teams = [x['name'] for x in resp['teams']]
        assert sorted(expected_teams) == sorted(actual_teams)

    if expected_orgs:
        actual_orgs = [x['name'] for x in resp['organizations']]
        assert sorted(expected_orgs) == sorted(actual_orgs)


@pytest.mark.deployment_standalone
@pytest.mark.parametrize("invalid_payload", [
    ({"email": "invalidemail"}, "Enter a valid email address."),
    ({"email": "@whoops"}, "Enter a valid email address."),
    ({"username": ""}, "This field may not be blank"),
    ({"password": "short"}, "This password is too short"),
    ({"password": ""}, "This password is too short"),
    ({"groups": [{"name": "HITHERE"}]}, "does not exist"),
    ({"teams": [{"name": "HITHERE"}]}, "does not exist"),
])
def test_ui_v2_user_create_invalid_data(
    settings,
    galaxy_client,
    invalid_payload,
    random_username,
):
    """Test user creation in ui/v2/users/ with invalid data."""

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
