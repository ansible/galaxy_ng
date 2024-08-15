import json
import os

import pytest

from galaxykit.client import GalaxyClient
from galaxykit.collections import upload_test_collection


pytestmark = pytest.mark.qa  # noqa: F821


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


@pytest.mark.skip(reason=(
    "the galaxy.collection_namespace_owner role is global"
    " and does not allow object assignment"
))
@pytest.mark.deployment_standalone
def test_dab_rbac_namespace_owner_by_user(
    settings,
    galaxy_client,
    random_namespace,
    random_username
):
    """Tests the galaxy.system_auditor role can be added to a user and has the right perms."""

    gc = galaxy_client("admin", ignore_cache=True)

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        if not os.environ.get("JWT_PROXY"):
            pytest.skip(reason="this only works with the jwtproxy")
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
@pytest.mark.skip(reason=(
    "the galaxy.collection_namespace_owner role is global"
    " and does not allow object assignment"
))
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
        if not os.environ.get("JWT_PROXY"):
            pytest.skip(reason="this only works with the jwtproxy")
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


@pytest.mark.deployment_standalone
def test_dab_user_platform_auditor_bidirectional_sync(
    settings,
    galaxy_client,
    random_username,
):
    """
    Integration test for the m2m and signals that copy user roles to roledefs
    and vice-versa for the galaxy.auditor and Platform Auditor role.

    * when given the galaxy.auditor role, the "Platform Auditor" roledef
      should also be granted automatically,
    * when revoking the galaxy.auditor role, the "Platform Auditor" roledef
      should also be revoked automatically,

    * when given the "Platform Auditor" roledef the galaxy.auditor role
      should also be granted automatically,
    * when revoking the "Platform Auditor" roledef the galaxy.auditor role
      should also be revoked automatically,
    """
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)

    # find the "platform auditor" roledef ...
    pa_def = gc.get('_ui/v2/role_definitions/?name=Platform%20Auditor')['results'][0]

    # make the user ...
    user_data = gc.post(
        "_ui/v2/users/",
        body=json.dumps({
            "username": random_username,
            "password": "redhat1234",
            "email": random_username + '@localhost'
        })
    )
    uid = user_data['id']

    ##################################################
    # PULP => DAB
    ##################################################

    # assign the galaxy.system_auditor role to the user
    pulp_assignment = gc.post(
        f"pulp/api/v3/users/{uid}/roles/",
        body=json.dumps({'content_object': None, 'role': 'galaxy.auditor'})
    )

    # ensure the user got the platform auditor roledef assignment
    urds = gc.get(f'_ui/v2/role_user_assignments/?user__id={uid}')
    assert urds['count'] == 1
    assert urds['results'][0]['role_definition'] == pa_def['id']

    # now remove the pulp role ..
    try:
        gc.delete(pulp_assignment['pulp_href'])
    except Exception:
        pass

    # ensure the user no longer has the roledef assignment
    urds = gc.get(f'_ui/v2/role_user_assignments/?user__id={uid}')
    assert urds['count'] == 0

    ##################################################
    # DAB => PULP
    ##################################################

    # assign the roledefinition ...
    roledef_assignment = gc.post(
        '_ui/v2/role_user_assignments/',
        body=json.dumps({
            'user': uid,
            'role_definition': pa_def['id'],
        })
    )

    # ensure the user got the pulp role assignment
    pulp_assignments = gc.get(f"pulp/api/v3/users/{uid}/roles/")
    assert pulp_assignments['count'] == 1
    assert pulp_assignments['results'][0]['role'] == 'galaxy.auditor'

    # remove the roledef ...
    try:
        gc.delete(roledef_assignment['url'])
    except Exception:
        pass

    pulp_assignments = gc.get(f"pulp/api/v3/users/{uid}/roles/")
    assert pulp_assignments['count'] == 0


@pytest.mark.deployment_standalone
def test_dab_team_platform_auditor_bidirectional_sync(
    settings,
    galaxy_client,
    random_username,
):
    """
    Integration test for the m2m and signals that copy group roles to
    team roledefs and vice-versa for the galaxy.auditor and Platform Auditor role.

    * when given the galaxy.auditor role, the "Platform Auditor" roledef
      should also be granted automatically,
    * when revoking the galaxy.auditor role, the "Platform Auditor" roledef
      should also be revoked automatically,

    * when given the "Platform Auditor" roledef the galaxy.auditor role
      should also be granted automatically,
    * when revoking the "Platform Auditor" roledef the galaxy.auditor role
      should also be revoked automatically,
    """
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)

    # find the "platform auditor" roledef ...
    pa_def = gc.get('_ui/v2/role_definitions/?name=Platform%20Auditor')['results'][0]

    org_name = random_username.replace('user_', 'org_')
    team_name = random_username.replace('user_', 'team_')

    # make the org ...
    gc.post(
        "_ui/v2/organizations/",
        body=json.dumps({"name": org_name})
    )

    # make the team ...
    team_data = gc.post(
        "_ui/v2/teams/",
        body=json.dumps({
            "name": team_name,
            "organization": org_name,
        })
    )
    teamid = team_data['id']
    guid = team_data['group']['id']

    ##################################################
    # PULP => DAB
    ##################################################

    # assign the galaxy.system_auditor role to the group
    pulp_assignment = gc.post(
        f"pulp/api/v3/groups/{guid}/roles/",
        body=json.dumps({'content_object': None, 'role': 'galaxy.auditor'})
    )

    # ensure the team got the platform auditor roledef assignment
    trds = gc.get(f'_ui/v2/role_team_assignments/?team__id={teamid}')
    assert trds['count'] == 1
    assert trds['results'][0]['role_definition'] == pa_def['id']

    # now remove the pulp role ..
    try:
        gc.delete(pulp_assignment['pulp_href'])
    except Exception:
        pass

    # ensure the team no longer has the roledef assignment
    trds = gc.get(f'_ui/v2/role_team_assignments/?team__id={teamid}')
    assert trds['count'] == 0

    ##################################################
    # DAB => PULP
    ##################################################

    # assign the roledefinition ...
    roledef_assignment = gc.post(
        '_ui/v2/role_team_assignments/',
        body=json.dumps({
            'team': teamid,
            'role_definition': pa_def['id'],
        })
    )

    # ensure the user got the pulp role assignment
    pulp_assignments = gc.get(f"pulp/api/v3/groups/{guid}/roles/")
    assert pulp_assignments['count'] == 1
    assert pulp_assignments['results'][0]['role'] == 'galaxy.auditor'

    # remove the roledef ...
    try:
        gc.delete(roledef_assignment['url'])
    except Exception:
        pass

    # ensure the role was removed
    pulp_assignments = gc.get(f"pulp/api/v3/groups/{guid}/roles/")
    assert pulp_assignments['count'] == 0
