import json
# import os

import pytest

from galaxykit.client import GalaxyClient
from galaxykit.collections import upload_test_collection


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
# @pytest.mark.skipif(
#    not os.getenv("ENABLE_DAB_TESTS"),
#    reason="Skipping test because ENABLE_DAB_TESTS is not set"
# )
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
# @pytest.mark.skipif(
#     not os.getenv("ENABLE_DAB_TESTS"),
#     reason="Skipping test because ENABLE_DAB_TESTS is not set"
# )
def test_dab_rbac_namespace_owner_by_user(
    settings,
    galaxy_client,
    random_namespace,
    random_username
):
    """Tests the galaxy.system_auditor role can be added to a user and has the right perms."""

    gc = galaxy_client("admin", ignore_cache=True)

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        # create the user in the proxy ...
        gc.post(
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
    auth = {'username': random_username, 'password': 'redhat1234'}
    ugc = GalaxyClient(gc.galaxy_root, auth=auth)
    me_ds = ugc.get('_ui/v1/me/')

    # find the role for namespace owner ...
    rd = gc.get('_ui/v2/role_definitions/?name=galaxy.collection_namespace_owner')
    role_id = rd['results'][0]['id']

    # assign the user role ...
    payload = {
        'user': me_ds['id'],
        'role_definition': role_id,
        'content_type': 'galaxy.namespace',
        'object_id': random_namespace['id'],
    }
    gc.post('_ui/v2/role_user_assignments/', body=payload)

    # try to update the namespace ...
    ugc.put(
        f"_ui/v1/namespaces/{random_namespace['name']}/",
        body=json.dumps({
            "name": random_namespace['name'],
            "company": "foobar",
        })
    )

    # try to upload a collection as the user...
    upload_test_collection(ugc, namespace=random_namespace['name'])


@pytest.mark.deployment_standalone
# @pytest.mark.skipif(
#    not os.getenv("ENABLE_DAB_TESTS"),
#    reason="Skipping test because ENABLE_DAB_TESTS is not set"
# )
def test_dab_rbac_namespace_owner_by_team(
    settings,
    galaxy_client,
    random_namespace,
    random_username
):
    """Tests the galaxy.system_auditor role can be added to a user and has the right perms."""

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("galaxykit uses drf tokens, which bypass JWT auth and claims processing")

    org_name = random_username.replace('user_', 'org_')
    team_name = random_username.replace('user_', 'team_')

    gc = galaxy_client("admin", ignore_cache=True)

    # make the user ...
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        # create the user in the proxy ...
        gc.post(
            "/api/gateway/v1/users/",
            body=json.dumps({"username": random_username, "password": "redhat1234"})
        )

        auth = {'username': random_username, 'password': 'redhat1234'}
        ugc = GalaxyClient(gc.galaxy_root, auth=auth)
        me_ds = ugc.get('_ui/v1/me/')
        user_id = me_ds['id']

    else:
        user_data = gc.post(
            "_ui/v2/users/",
            body=json.dumps({
                "username": random_username,
                "password": "redhat1234",
                "email": random_username + '@localhost'
            })
        )
        user_id = user_data['id']
        auth = {'username': random_username, 'password': 'redhat1234'}
        ugc = GalaxyClient(gc.galaxy_root, auth=auth)

    # make the team ...
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:

        # create an org (Default doesn't sync)
        org_data = gc.post(
            "/api/gateway/v1/organizations/",
            body=json.dumps({"name": org_name})
        )
        org_id = org_data['id']

        # create a team
        team_data = gc.post(
            "/api/gateway/v1/teams/",
            body=json.dumps({"name": team_name, "organization": org_id})
        )
        team_id = team_data['id']

        # get the gateway's userid for this user ...
        # FIXME - pagination or filtering support?
        users_data = gc.get(
            "/api/gateway/v1/users/",
        )
        gateway_uid = None
        for user in users_data['results']:
            if user['username'] == random_username:
                gateway_uid = user['id']
                break

        # add user to the team
        #   Unforunately the API contract for this endpoint is to return
        #   HTTP/1.1 204 No Content ... which means galaxyclient blows up
        #   on a non-json response.
        try:
            gc.post(
                f"/api/gateway/v1/teams/{team_id}/users/associate/",
                body=json.dumps({"instances": [gateway_uid]})
            )
        except Exception:
            pass

        '''
        # FIXME - galaxykit only wants to use tokens, which bypasses
        #        jwt & claims processing

        # check memberships in galaxy ...
        me_rr = ugc.get(f'_ui/v1/me/', use_token=False)
        #user_rr = ugc.get(f'_ui/v2/users/?username={random_username}')
        import epdb; epdb.st()
        '''

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

    # find the role for namespace owner ...
    rd = gc.get('_ui/v2/role_definitions/?name=galaxy.collection_namespace_owner')
    role_id = rd['results'][0]['id']

    # assign the team role ...
    payload = {
        'team': team_id,
        'role_definition': role_id,
        'object_id': str(random_namespace['id']),
    }
    gc.post('_ui/v2/role_team_assignments/', body=payload)

    # try to update the namespace ...
    ugc.put(
        f"_ui/v1/namespaces/{random_namespace['name']}/",
        body=json.dumps({
            "name": random_namespace['name'],
            "company": "foobar",
        })
    )

    # try to upload a collection as the user...
    upload_test_collection(ugc, namespace=random_namespace['name'])
