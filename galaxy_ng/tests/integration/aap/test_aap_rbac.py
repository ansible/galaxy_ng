import json
import os

import pytest

# from galaxykit.client import GalaxyClient
from galaxykit.client import BasicAuthClient
# from galaxykit.collections import upload_test_collection
# from galaxykit.utils import wait_for_task
# from galaxy_ng.tests.integration.utils import set_certification


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_standalone
@pytest.mark.skipif(
    not os.environ.get('JWT_PROXY'),
    reason="relies on jwt proxy"
)
def test_aap_service_index_and_claims_processing(
    settings,
    ansible_config,
    galaxy_client,
    random_username
):

    gc = galaxy_client("admin", ignore_cache=True)
    ga = BasicAuthClient(gc.galaxy_root, 'admin', 'admin')

    org_name = random_username.replace('user_', 'org_')
    team_name = random_username.replace('user_', 'team_')
    group_name = org_name + '::' + team_name

    # make the org in the gateway
    org_data = ga.post(
        '/api/gateway/v1/organizations/',
        body=json.dumps({'name': org_name})
    )

    # make the team in the gateway
    team_data = ga.post(
        '/api/gateway/v1/teams/',
        body=json.dumps({'name': team_name, 'organization': org_data['id']})
    )

    # make the user in the gateway
    user_data = ga.post(
        '/api/gateway/v1/users/',
        body=json.dumps({'username': random_username, 'password': 'redhat1234'})
    )

    # get all of gateway's roledefs ...
    gateway_roledefs = ga.get('/api/gateway/v1/role_definitions/')
    gateway_roledefs = dict((x['name'], x) for x in gateway_roledefs['results'])

    # get all of galaxy's roledefs ...
    galaxy_roledefs = ga.get('/api/galaxy/_ui/v2/role_definitions/')
    galaxy_roledefs = dict((x['name'], x) for x in galaxy_roledefs['results'])

    # make the user a team member in the gateway ...
    ga.post(
        '/api/gateway/v1/role_user_assignments/',
        body=json.dumps({
            'user': user_data['id'],
            'role_definition': gateway_roledefs['Team Member']['id'],
            'object_id': team_data['id'],
        })
    )

    # access galaxy as the user to process claims ...
    uc = BasicAuthClient(gc.galaxy_root, random_username, 'redhat1234')
    new_data = uc.get(f'/api/galaxy/_ui/v2/users/?username={random_username}')
    assert new_data['count'] == 1
    new_user = new_data['results'][0]
    assert new_user['username'] == random_username

    # the inheritied orgs should not show memberships ...
    assert not new_user['organizations']

    # the team should be shown ...
    new_teams = [x['name'] for x in new_user['teams']]
    assert new_teams == [team_name]

    # delete the user in the gateway ...
    uid = user_data['id']
    rr = ga.delete(f'/api/gateway/v1/users/{uid}/', parse_json=False)

    # make sure the user is gone from galaxy ...
    rr = ga.get(f'/api/galaxy/_ui/v2/users/?username={random_username}')
    assert rr['count'] == 0

    # delete the team in the gateway
    tid = team_data['id']
    rr = ga.delete(f'/api/gateway/v1/teams/{tid}/', parse_json=False)

    # make sure the team is gone from galaxy ...
    rr = ga.get(f'/api/galaxy/_ui/v2/teams/?name={team_name}')
    assert rr['count'] == 0

    # FIXME: cascade delete on the group from the team isn't working
    # rr = ga.get(f'/api/galaxy/_ui/v2/groups/?name={group_name}')
    # assert rr['count'] == 0

    # delete the org in the gateway
    oid = org_data['id']
    rr = ga.delete(f'/api/gateway/v1/organizations/{oid}/', parse_json=False)

    # make sure the org is gone from galaxy ...
    rr = ga.get(f'/api/galaxy/_ui/v2/organizations/?name={org_name}')
    assert rr['count'] == 0
