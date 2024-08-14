import json
import os
from collections import namedtuple

import pytest
from ..utils.client_basic import BasicAuthClient
from ..utils import set_certification


from galaxykit.client import GalaxyClient
from galaxykit.collections import upload_test_collection


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.fixture
def namespace_object_owner_roledef(galaxy_client):

    roledef_name = 'galaxy.collection_namespace_object_owner'

    gc = galaxy_client("admin", ignore_cache=True)

    roledefs = gc.get("_ui/v2/role_definitions/")
    roledefs = dict((x['name'], x) for x in roledefs['results'])

    if roledef_name in roledefs:
        return roledefs[roledef_name]

    payload = {
        'name': roledef_name,
        'content_type': 'galaxy.namespace',
        'permissions': [
            'galaxy.change_namespace',
            'galaxy.upload_to_namespace'
        ],
    }
    return gc.post("_ui/v2/role_definitions/", body=json.dumps(payload))


@pytest.fixture
def collection_object_owner_roledef(galaxy_client):

    roledef_name = 'galaxy.collection_object_owner4'

    gc = galaxy_client("admin", ignore_cache=True)

    roledefs = gc.get("_ui/v2/role_definitions/")
    roledefs = dict((x['name'], x) for x in roledefs['results'])

    if roledef_name in roledefs:
        return roledefs[roledef_name]

    payload = {
        'name': roledef_name,
        'content_type': 'galaxy.collection',
        'permissions': [
            'galaxy.view_collection',
            'galaxy.change_collection',
            'ansible.delete_collection',
        ],
    }
    #import epdb; epdb.st()
    return gc.post("_ui/v2/role_definitions/", body=json.dumps(payload))



@pytest.fixture
def random_user_client(
    settings,
    galaxy_client,
    random_username,
):

    gc = galaxy_client("admin", ignore_cache=True)

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:

        # Need galaxykit to use basic auth ...
        gw = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

        # create the user in the proxy ...
        user = gw.post(
            "/api/gateway/v1/users/",
            body=json.dumps({"username": random_username, "password": "redhat1234"})
        )

    else:
        # create the user in ui/v2 ...
        gc.post(
            "_ui/v2/users/",
            body=json.dumps({
                "username": random_username,
                "email": random_username + '@localhost',
                "password": "redhat1234"}
            )
        )

    # get the user's galaxy level details ...
    ugc = BasicAuthClient(gc.galaxy_root, random_username, 'redhat1234')
    ugc.get('_ui/v1/me/')

    return ugc


@pytest.fixture
def random_team_with_user_client(
    settings,
    galaxy_client,
    random_user_client,
):

    random_username = random_user_client.username
    org_name = random_username.replace('user_', 'org_')
    team_name = random_username.replace('user_', 'team_')

    gc = galaxy_client("admin", ignore_cache=True)
    ugc = random_user_client

    # make the team ...
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:

        gw = BasicAuthClient(gc.galaxy_root, gc.username, gc.password)

        # get the gateway's userid for this user ...
        user_data = random_user_client.get('/api/gateway/v1/me/')['results'][0]
        gateway_uid = user_data['id']

        # create an org (Default doesn't sync)
        org_data = gw.post(
            "/api/gateway/v1/organizations/",
            body=json.dumps({"name": org_name})
        )
        org_id = org_data['id']

        # create a team
        team_data = gw.post(
            "/api/gateway/v1/teams/",
            body=json.dumps({"name": team_name, "organization": org_id})
        )
        team_id = team_data['id']

        gw.post(
            f"/api/gateway/v1/teams/{team_id}/users/associate/",
            body=json.dumps({"instances": [gateway_uid]}),
            want_json=False,
        )

        # force user claims to process ...
        ugc.get(f'_ui/v2/users/?username={random_username}')

    else:
        team_data = gc.post(
            "_ui/v2/teams/",
            body=json.dumps({
                "name": team_name,
            })
        )
        team_id = team_data['id']

        # add the user to the team ...
        gc.post(
            f'_ui/v2/teams/{team_id}/users/associate/',
            body=json.dumps({'instances': [user_id]})
        )

    return (team_data, ugc)


@pytest.mark.skip(reason="we are not aiming for 1:1 anymore")
@pytest.mark.deployment_standalone
def test_dab_roledefs_match_pulp_roles(galaxy_client):
    gc = galaxy_client("admin", ignore_cache=True)
    roles = gc.get('pulp/api/v3/roles/?name__startswith=galaxy')
    roledefs = gc.get('_ui/v2/role_definitions/')

    roledefmap = dict((x['name'], x) for x in roledefs['results'])

    missing = []
    for role in roles['results']:
        if role['name'] not in roledefmap:
            missing.append(role['name'])

    assert not missing

    ''' FIXME ...
    # validate permissions ...
    for role in roles['results']:
        roledef = roledefmap[role['name']]
        import epdb; epdb.st()

    import epdb; epdb.st()
    '''


@pytest.mark.deployment_standalone
@pytest.mark.parametrize("assignment_type", ["user", "team"])
def test_dab_rbac_namespace_object_owner_by_user_or_team(
    assignment_type,
    ansible_config,
    settings,
    galaxy_client,
    random_namespace,
    namespace_object_owner_roledef,
    collection_object_owner_roledef,
    random_team_with_user_client,
):
    """Tests the galaxy.system_auditor role can be added to a user and has the right perms."""

    team_data = random_team_with_user_client[0]
    ugc = random_team_with_user_client[1]

    random_username = ugc.username
    org_name = random_username.replace('user_', 'org_')
    team_name = random_username.replace('user_', 'team_')

    gc = galaxy_client("admin", ignore_cache=True)

    if assignment_type == 'user':
        # get the galaxy level user info ...
        me_ds = ugc.get('_ui/v1/me/')

        # assign the user role ...
        payload = {
            'user': me_ds['id'],
            'role_definition': namespace_object_owner_roledef['id'],
            'object_id': str(random_namespace['id']),
        }
        gc.post('_ui/v2/role_user_assignments/', body=payload)

    else:
        # get the galaxy level team info ...
        gteam_data = gc.get(f'_ui/v2/teams/?name={team_name}')['results'][0]
        team_id = gteam_data['id']

        # assign the team role ...
        payload = {
            'team': team_id,
            'role_definition': namespace_object_owner_roledef['id'],
            'object_id': str(random_namespace['id']),
        }
        gc.post('_ui/v2/role_team_assignments/', body=payload)

    # try to update the namespace ...
    company_resp = ugc.put(
        f"_ui/v1/namespaces/{random_namespace['name']}/",
        body=json.dumps({
            "name": random_namespace['name'],
            "company": "foobar",
        })
    )
    assert company_resp['company'] == 'foobar'

    # try to upload a collection as the user...
    col = upload_test_collection(ugc, namespace=random_namespace['name'])
    Artifact = namedtuple('Artifact', ['name', 'namespace', 'published', 'version'])
    artifact = Artifact(**col)
    assert artifact.namespace == random_namespace['name']

    # certify the collection ...
    if settings.get('GALAXY_REQUIRE_CONTENT_APPROVAL') == True:
        set_certification(ansible_config(), gc, artifact)

    # get the collection detail ...
    #col_data = ugc.get(f"v3/plugin/ansible/content/published/collections/index/{artifact.namespace}/{artifact.name}/")
    col_data = ugc.get(f"_ui/v2/collections/?namespace={artifact.namespace}&name={artifact.name}")
    col_data = col_data['results'][0]
    col_id = col_data['pulp_id']

    # grant collection owner role ...
    if assignment_type == 'user':
        # get the galaxy level user info ...
        me_ds = ugc.get('_ui/v1/me/')

        # assign the user role ...
        payload = {
            'user': me_ds['id'],
            'role_definition': collection_object_owner_roledef['id'],
            #'object_id': col_id,
        }
        gc.post('_ui/v2/role_user_assignments/', body=payload)

    else:
        # get the galaxy level team info ...
        gteam_data = gc.get(f'_ui/v2/teams/?name={team_name}')['results'][0]
        team_id = gteam_data['id']

        # assign the team role ...
        payload = {
            'team': team_id,
            'role_definition': collection_object_owner_roledef['id'],
            'object_id': col_id,
        }
        gc.post('_ui/v2/role_team_assignments/', body=payload)

    #import epdb; epdb.st()
    # try to delete the collection ...
    resp = ugc.delete(
        f"v3/plugin/ansible/content/published/collections/index/{col['namespace']}/{col['name']}/versions/{col['version']}/"
    )
    import epdb; epdb.st()
