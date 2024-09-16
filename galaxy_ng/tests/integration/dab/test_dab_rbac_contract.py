from http import HTTPStatus

import pytest
from galaxykit import GalaxyClient
from galaxykit.utils import GalaxyClientError

from galaxy_ng.tests.integration.utils.tools import random_name
from galaxy_ng.tests.integration.utils.teams import add_user_to_team


GALAXY_API_PATH_PREFIX = "/api/galaxy"  # cant import from settings on integration tests


# This tests the basic DAB RBAC contract using custom roles to do things.
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_list_namespace_permissions(galaxy_client):
    gc = galaxy_client("admin")
    r = gc.get("_ui/v2/role_metadata/")
    assert "galaxy.namespace" in r["allowed_permissions"]
    allowed_perms = r["allowed_permissions"]["galaxy.namespace"]
    assert set(allowed_perms) == {
        "galaxy.change_namespace",
        "galaxy.delete_namespace",
        "galaxy.add_collectionimport",
        "galaxy.change_collectionimport",
        "galaxy.delete_collectionimport",
        "galaxy.upload_to_namespace",
        "galaxy.view_collectionimport",
        "galaxy.view_namespace",
    }


# look for the content_type choices
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_role_definition_options(galaxy_client):
    gc = galaxy_client("admin")
    # TODO: add support for options in GalaxyClient in galaxykit
    galaxy_root = gc.galaxy_root
    api_prefix = galaxy_root[gc.galaxy_root.index('/api/'):]
    options_r = gc._http("options", api_prefix + "_ui/v2/role_definitions/")
    assert "actions" in options_r
    assert "POST" in options_r["actions"]
    assert "permissions" in options_r["actions"]["POST"]
    post_data = options_r["actions"]["POST"]
    assert "permissions" in post_data
    field_data = post_data["permissions"]
    assert "child" in field_data
    assert "choices" in field_data["child"]

    assert {
        "galaxy.change_namespace",
        "galaxy.add_namespace",
        "galaxy.delete_namespace",
        "galaxy.add_collectionimport",
        "galaxy.change_collectionimport",
        "galaxy.delete_collectionimport",
        "galaxy.upload_to_namespace",
        "galaxy.view_collectionimport",
        "galaxy.view_namespace",
        "shared.add_team",
        "shared.change_team",
        "shared.delete_team",
        "shared.view_team",
    }.issubset(set(item["value"] for item in field_data["child"]["choices"]))

    assert "content_type" in post_data
    field_data = post_data["content_type"]
    assert "choices" in field_data

    assert {
        "galaxy.collectionimport",
        "galaxy.namespace",
        "shared.team",
    }.issubset(set(item["value"] for item in field_data["choices"]))


# This is role data that works in both DAB and pulp roles.
NS_FIXTURE_DATA = {
    "name": "galaxy.namespace_custom_system_role",
    "description": "A description for my new role from FIXTURE_DATA",
    "permissions": [
        "galaxy.change_namespace",
        "galaxy.delete_namespace",
        "galaxy.view_namespace",
        "galaxy.view_collectionimport",
    ],
}

DAB_ROLE_URL = "_ui/v2/role_definitions/"
PULP_ROLE_URL = "pulp/api/v3/roles/"


# These fixtures are function-scoped, so they will be deleted.
# Deleting the role will delete all associated permissions.
@pytest.fixture
def custom_role_factory(request, galaxy_client):
    def inner(data, url_base=DAB_ROLE_URL):
        gc = galaxy_client("admin")

        def delete_role():
            if "id" in role:
                response = gc.delete(f'{url_base}{role["id"]}/', parse_json=False)
            elif "pulp_href" in role:
                response = gc.delete(role["pulp_href"], parse_json=False)
            else:
                raise RuntimeError(f"Could not figure out how to delete {role}")
            assert response.status_code == HTTPStatus.NO_CONTENT

        roles_list = gc.get(url_base, params={"name": data['name']})
        if roles_list["count"] > 1:
            raise RuntimeError(f"Found too many {url_base} with expected name {data['name']}")
        if roles_list["count"] == 1:
            role = roles_list["results"][0]
            # FIXME(cutwater): Direct function call that relies on closure is rather obscure
            #   Better to pass parameters explicitly.
            delete_role()

        role = gc.post(url_base, body=data)
        request.addfinalizer(delete_role)
        return role

    return inner


@pytest.fixture
def namespace(galaxy_client):
    gc = galaxy_client("admin")

    namespace = gc.post("_ui/v1/my-namespaces/", body={"name": random_name("namespace", sep="_")})

    yield namespace

    response = gc.delete(f"_ui/v1/my-namespaces/{namespace['name']}/", parse_json=False)
    assert response.status_code == HTTPStatus.NO_CONTENT


@pytest.fixture
def team(galaxy_client):
    gc = galaxy_client("admin")

    team = gc.post('_ui/v2/teams/', body={"name": random_name("team")})

    yield team

    response = gc.delete(f"_ui/v2/teams/{team['id']}/", parse_json=False)
    assert response.status_code == HTTPStatus.NO_CONTENT


def assert_role_assignment_fields(summary_fields: dict, related: dict, expected_fields: set):
    assert expected_fields.issubset(summary_fields)
    assert expected_fields.issubset(related)

    # assert each entry has at least the id field
    for field in expected_fields:
        assert "id" in summary_fields[field]

    # assert related includes relative urls
    for field in expected_fields:
        assert related[field].startswith(GALAXY_API_PATH_PREFIX)


# NOTE(cutwater): The goal is to check that assignment is duplicated in both systems.
def assert_object_role_assignments(gc, user, namespace, expected=0):
    # Assure the assignment shows up in the pulp API
    data = gc.get(f"_ui/v1/my-namespaces/{namespace['name']}/")
    assert len(data["users"]) == expected

    # Assure the assignment shows up in the DAB RBAC API
    data = gc.get(
        "_ui/v2/role_user_assignments/",
        params={"user": user['id'], "object_id": namespace['id']}
    )
    assert data["count"] == expected

    if not expected:
        return

    assert_role_assignment_fields(
        summary_fields=data["results"][0]["summary_fields"],
        related=data["results"][0]["related"],
        expected_fields={"created_by", "role_definition", "user", "content_object"},
    )


def check_system_role_user_assignments(client: GalaxyClient, user: dict, role: dict) -> bool:
    data = client.get(
        "_ui/v2/role_user_assignments/",
        params={"user": user['id'], "role_definition": role['id'], "content_type__isnull": "True"},
    )
    if not data["count"]:
        return False

    assert data["count"] == 1

    assert_role_assignment_fields(
        summary_fields=data["results"][0]["summary_fields"],
        related=data["results"][0]["related"],
        expected_fields={"created_by", "role_definition", "user"},
    )
    return True


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.parametrize("by_api", ["dab", "pulp"])
def test_create_custom_namespace_system_admin_role(custom_role_factory, galaxy_client, by_api):
    if by_api == "dab":
        system_ns_role = custom_role_factory({**NS_FIXTURE_DATA, "content_type": None})
    else:
        system_ns_role = custom_role_factory(NS_FIXTURE_DATA, url_base=PULP_ROLE_URL)

    assert system_ns_role["name"] == NS_FIXTURE_DATA["name"]

    gc = galaxy_client("admin")
    roles_list = gc.get(DAB_ROLE_URL, params={"name": NS_FIXTURE_DATA['name']})
    assert roles_list["count"] == 1
    dab_role = roles_list["results"][0]
    assert set(dab_role["permissions"]) == set(NS_FIXTURE_DATA["permissions"])

    roles_list = gc.get(PULP_ROLE_URL, params={"name": NS_FIXTURE_DATA['name']})
    assert roles_list["count"] == 1
    pulp_role = roles_list["results"][0]
    assert set(pulp_role["permissions"]) == set(NS_FIXTURE_DATA["permissions"])


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_give_user_custom_role_system(settings, galaxy_client, custom_role_factory, namespace):

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT', True) is not True:
        pytest.skip("this test relies on local resource creation")

    # TODO: verify that assignment is seen in pulp API (HOW?)
    # Step 0: Setup test.

    system_ns_role = custom_role_factory(NS_FIXTURE_DATA)
    admin_client = galaxy_client("admin")

    user_client = galaxy_client("basic_user")
    user = user_client.get("_ui/v1/me/")

    # Step 1: Check that regular user doesn't have write access to a namespace.

    with pytest.raises(GalaxyClientError) as ctx:
        user_client.put(
            f"_ui/v1/namespaces/{namespace['name']}/", body={
                **namespace,
                "company": "Test RBAC Company 1",
            }
        )
    assert ctx.value.response.status_code == HTTPStatus.FORBIDDEN

    # Step 2: Assign system role to a user

    role_assignment = admin_client.post(
        "_ui/v2/role_user_assignments/",
        body={"role_definition": system_ns_role["id"], "user": user["id"]},
    )
    role_definition_summary = role_assignment["summary_fields"]["role_definition"]
    assert role_definition_summary["name"] == NS_FIXTURE_DATA["name"]
    assert role_definition_summary["description"] == NS_FIXTURE_DATA["description"]
    assert check_system_role_user_assignments(admin_client, user, system_ns_role)

    # Step 3: Check that user with assigned system role has write access to a namespace.

    response = user_client.put(
        f"_ui/v1/namespaces/{namespace['name']}/", body={
            **namespace,
            "company": "Test RBAC Company 2",
        }
    )
    assert response["company"] == "Test RBAC Company 2"

    # Step 4: Revoke system role from a user.

    response = admin_client.delete(
        f"_ui/v2/role_user_assignments/{role_assignment['id']}/",
        parse_json=False
    )
    assert response.status_code == HTTPStatus.NO_CONTENT
    assert not check_system_role_user_assignments(admin_client, user, system_ns_role)

    # Step 5: Check that user with revoked system role doesn't have write access to a namespace.

    with pytest.raises(GalaxyClientError) as ctx:
        user_client.put(
            f"_ui/v1/namespaces/{namespace['name']}/", body={
                **namespace,
                "company": "Test RBAC Company 3",
            }
        )
    assert ctx.value.response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_give_team_custom_role_system(
    settings,
    galaxy_client,
    custom_role_factory,
    team,
    namespace,
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT', True) is not True:
        pytest.skip("galaxykit uses drf tokens, which bypass JWT auth and claims processing")

    # Step 0: Setup test.

    system_ns_role = custom_role_factory(NS_FIXTURE_DATA)
    admin_client = galaxy_client("admin")

    user_client = galaxy_client("basic_user")
    user = user_client.get("_ui/v1/me/")
    add_user_to_team(admin_client, userid=user["id"], teamid=team["id"])

    # Step 1: Check that regular user doesn't have write access to a namespace.

    with pytest.raises(GalaxyClientError) as ctx:
        user_client.put(
            f"_ui/v1/namespaces/{namespace['name']}/", body={
                **namespace,
                "company": "Test RBAC Company 1",
            }
        )
    assert ctx.value.response.status_code == HTTPStatus.FORBIDDEN

    # Step 2: Assign system role to a team

    role_assignment = admin_client.post(
        "_ui/v2/role_team_assignments/",
        body={"role_definition": system_ns_role["id"], "team": team["id"]},
    )
    role_definition_resp = role_assignment["summary_fields"]["role_definition"]
    assert role_definition_resp["name"] == NS_FIXTURE_DATA["name"]
    assert role_definition_resp["description"] == NS_FIXTURE_DATA["description"]

    # Step 3: Check that user with assigned system role has write access to a namespace.
    response = user_client.put(
        f"_ui/v1/namespaces/{namespace['name']}/", body={
            **namespace,
            "company": "Test RBAC Company 2",
        }
    )
    assert response["company"] == "Test RBAC Company 2"

    # Step 4: Revoke system role from a user.

    response = admin_client.delete(
        f"_ui/v2/role_team_assignments/{role_assignment['id']}/",
        parse_json=False
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Step 5: Check that user with revoked system role doesn't have write access to a namespace.

    with pytest.raises(GalaxyClientError) as ctx:
        user_client.put(
            f"_ui/v1/namespaces/{namespace['name']}/", body={
                **namespace,
                "company": "Test RBAC Company 3",
            }
        )
    assert ctx.value.response.status_code == HTTPStatus.FORBIDDEN


# TODO: We need another version of it for a team
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.parametrize("by_role_api", ["dab", "pulp"])
@pytest.mark.parametrize("by_assignment_api", ["dab", "pulp"])
def test_give_user_custom_role_object(
    galaxy_client,
    custom_role_factory,
    namespace,
    by_role_api,
    by_assignment_api
):
    admin_client = galaxy_client("admin")

    if by_role_api == 'pulp' and by_assignment_api == 'dab':
        pytest.skip(
            'This is not supported, the compatbility shim'
            + ' is only for the pulp assignment API'
        )

    if by_role_api == "dab":
        data = NS_FIXTURE_DATA.copy()
        data["name"] = "galaxy.namespace_custom_dab_object_role"
        data["content_type"] = "galaxy.namespace"
        custom_obj_role_dab = custom_role_factory(data)
        custom_obj_role_pulp = admin_client.get(
            PULP_ROLE_URL, params={"name": data['name']}
        )['results'][0]
    else:
        data = NS_FIXTURE_DATA.copy()
        data["name"] = "galaxy.namespace_custom_pulp_object_role"
        custom_obj_role_pulp = custom_role_factory(data, url_base=PULP_ROLE_URL)
        custom_obj_role_dab = admin_client.get(
            DAB_ROLE_URL, params={"name": data['name']}
        )['results'][0]

    # NOTE: If basic_user doesn't suffice, the dab proxy supports creating users
    #  and syncing them down to galaxy

    user_client = galaxy_client("basic_user")
    user = user_client.get("_ui/v1/me/")

    # sanity - assignments should not exist at start of this test
    assert_object_role_assignments(admin_client, user, namespace, 0)

    # Give the user permission to the namespace object
    dab_assignment = None
    if by_assignment_api == "dab":
        dab_assignment = admin_client.post(
            "_ui/v2/role_user_assignments/",
            body={
                "role_definition": custom_obj_role_dab["id"],
                "user": user["id"],
                "object_id": str(namespace["id"]),
            },
        )
    else:
        payload = {
            "name": namespace["name"],
            "users": [
                {
                    "id": user["id"],
                    "object_roles": [custom_obj_role_pulp["name"]],
                }
            ],
        }
        admin_client.put(f"_ui/v1/my-namespaces/{namespace['name']}/", body=payload)

    # TODO: make a request as the user and see that it works
    # NOTE: Check if user can have a minimal permission to modify namespace attributes
    #   (e.g. description, company, etc.)
    # NOTE: Check after permission is revoked, user cannot perform same operations

    assert_object_role_assignments(admin_client, user, namespace, 1)

    # Remove the permission from before
    if by_assignment_api == "dab":
        response = admin_client.delete(
            f"_ui/v2/role_user_assignments/{dab_assignment['id']}/",
            parse_json=False
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
    else:
        payload = {
            "name": namespace["name"],
            "users": [],
        }
        admin_client.put(f"_ui/v1/my-namespaces/{namespace['name']}/", body=payload)

    assert_object_role_assignments(admin_client, user, namespace, 0)


@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.deployment_standalone
def test_give_team_custom_role_object(
    settings,
    galaxy_client,
    custom_role_factory,
    namespace,
    team,
):
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT', True) is not True:
        pytest.skip("galaxykit uses drf tokens, which bypass JWT auth and claims processing")

    # Step 0: Setup test.

    admin_client = galaxy_client("admin")

    user_client = galaxy_client("basic_user")
    user = user_client.get("_ui/v1/me/")
    add_user_to_team(admin_client, userid=user["id"], teamid=team["id"])

    data = {
        "name": "galaxy.namespace_custom_object_role",
        "content_type": "galaxy.namespace",
        "description": "Galaxy namespace custom object role",
        "permissions": [
            "galaxy.change_namespace",
            "galaxy.delete_namespace",
            "galaxy.view_namespace",
        ],
    }
    custom_obj_role_dab = custom_role_factory(data)

    # Step 1: Check that regular user doesn't have write access to a namespace.
    with pytest.raises(GalaxyClientError) as ctx:
        user_client.put(
            f"_ui/v1/namespaces/{namespace['name']}/", body={
                **namespace,
                "company": "Test RBAC Company 1",
            }
        )
    assert ctx.value.response.status_code == HTTPStatus.FORBIDDEN

    # Step 2: Assign object role to a team

    admin_client.post(
        "_ui/v2/role_team_assignments/",
        body={
            "team": team["id"],
            "role_definition": custom_obj_role_dab["id"],
            "content_type": "galaxy.namespace",
            "object_id": str(namespace["id"]),
        },
    )

    # Step 3: Check that user with assigned system role has write access to a namespace.

    namespace = user_client.get(f"_ui/v1/namespaces/{namespace['name']}/")
    namespace = user_client.put(
        f"_ui/v1/namespaces/{namespace['name']}/", body={
            **namespace,
            "company": "Test RBAC Company 2",
        }
    )
    assert namespace["company"] == "Test RBAC Company 2"

    role_assignment = admin_client.get(
        "_ui/v2/role_team_assignments/",
        params={"object_id": namespace["id"]}
    )["results"][0]

    response = admin_client.delete(
        f"_ui/v2/role_team_assignments/{role_assignment['id']}/",
        parse_json=False
    )
    assert response.status_code == HTTPStatus.NO_CONTENT

    # Step 5: Check that user with revoked object role doesn't have write access to a namespace.

    with pytest.raises(GalaxyClientError) as ctx:
        user_client.put(
            f"_ui/v1/namespaces/{namespace['name']}/", body={
                **namespace,
                "company": "Test RBAC Company 3",
            }
        )
    assert ctx.value.response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.min_hub_version("4.10dev")
def test_object_role_permission_validation(galaxy_client, custom_role_factory, namespace):
    gc = galaxy_client("admin")

    data = NS_FIXTURE_DATA.copy()
    data["name"] = "galaxy.namespace_custom_pulp_object_role"
    # Add a permission not valid for namespaces
    data["permissions"] += ["core.view_task"]
    custom_obj_role_pulp = custom_role_factory(data, url_base=PULP_ROLE_URL)

    user_r = gc.get("_ui/v2/users/")
    assert user_r["count"] > 0
    user = user_r["results"][0]

    payload = {
        "name": namespace["name"],
        "users": [
            {
                "id": user["id"],
                "object_roles": [custom_obj_role_pulp["name"]],
            }
        ],
    }
    with pytest.raises(GalaxyClientError) as exc:
        gc.put(f"_ui/v1/my-namespaces/{namespace['name']}/", body=payload)
    assert 'Role type global does not match object namespace' in str(exc)


@pytest.fixture
def assert_user_in_group(galaxy_client):
    def _rf(user_id, group_id, expected=True):
        gc = galaxy_client("admin")
        user = gc.get(f"_ui/v2/users/{user_id}/")
        group = gc.get(f"_ui/v2/groups/{group_id}/")
        if expected:
            assert group["name"] in [g["name"] for g in user["groups"]]
        else:
            assert group["name"] not in [g["name"] for g in user["groups"]]

        assignment_r = gc.get(
            "_ui/v2/role_user_assignments/",
            params={
                "user": user['id'],
                "content_type__model": "team",
                "role_definition__name": "Galaxy Team Member"
            },
        )
        group_ids = [assignment["object_id"] for assignment in assignment_r["results"]]
        if expected:
            assert str(group_id) in group_ids, assignment_r
        else:
            assert str(group_id) not in group_ids, assignment_r
    return _rf


@pytest.fixture
def user_and_group(request, galaxy_client):
    "Return a tuple of a user and group where the user is not in the group"
    gc = galaxy_client("admin")
    user_r = gc.get("_ui/v2/users/", params={"username": "jdoe"})
    assert user_r["count"] > 0
    user = user_r["results"][0]

    group_r = gc.get("_ui/v2/groups/", params={"name": "ship_crew"})
    assert group_r["count"] > 0
    group = group_r["results"][0]

    def assure_user_not_in_group():
        # Remove the user from the group if they are in the group
        if "ship_crew" in [g["name"] for g in user["groups"]]:
            user["groups"] = [g for g in user["groups"] if g["name"] != "ship_crew"]
            gc.patch(f"_ui/v2/users/{user['id']}/", body={"groups": user["groups"]})

    assure_user_not_in_group()

    request.addfinalizer(assure_user_not_in_group)

    return (user, group)


@pytest.mark.min_hub_version("4.10dev")
def test_group_sync_from_pulp_to_dab(galaxy_client, assert_user_in_group, user_and_group):
    gc = galaxy_client("admin")
    user, group = user_and_group

    assert_user_in_group(user["id"], group["id"], expected=False)
    old_groups = user["groups"].copy()
    user["groups"].append(group)

    gc.patch(f"_ui/v2/users/{user['id']}/", body={"groups": user["groups"]})
    assert_user_in_group(user["id"], group["id"], expected=True)

    gc.patch(f"_ui/v2/users/{user['id']}/", body={"groups": old_groups})
    assert_user_in_group(user["id"], group["id"], expected=False)


@pytest.mark.skip(reason="FIXME - skip until resource management is decided")
def test_team_member_sync_from_dab_to_pulp(galaxy_client, assert_user_in_group, user_and_group):
    gc = galaxy_client("admin")
    user, group = user_and_group

    assert_user_in_group(user["id"], group["id"], expected=False)

    # Get the DAB team member role
    rd_list = gc.get("_ui/v2/role_definitions/", params={"name": "Galaxy Team Member"})
    assert rd_list["count"] == 1
    rd = rd_list["results"][0]

    # Because group and team are different, we look up the team by name, for DAB
    team_list = gc.get("_ui/v2/teams/", params={"name": group['name']})
    assert team_list["count"] == 1, team_list
    team = team_list["results"][0]

    gc.post(
        "_ui/v2/role_user_assignments/",
        body={
            "role_definition": rd["id"],
            "user": user["id"],
            "object_id": str(team["id"]),
        },
    )

    assert_user_in_group(user["id"], group["id"], expected=True)


@pytest.mark.min_hub_version("4.10dev")
def test_team_members_are_migrated(galaxy_client, assert_user_in_group):
    "Make sure any existing team memberships are correct"
    gc = galaxy_client("admin")

    team_assignments = gc.get("_ui/v2/role_user_assignments/", params={
        "role_definition__name": "Galaxy Team Member"
    })
    for assignment in team_assignments["results"]:
        assert_user_in_group(assignment["user"], int(assignment["object_id"]))
