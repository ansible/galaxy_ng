import json
import os
from collections import namedtuple

import pytest

from galaxykit.client import GalaxyClient
from galaxykit.collections import upload_test_collection
from galaxykit.utils import wait_for_task

from ..utils import set_certification
from ..utils.teams import add_user_to_team


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


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.skipif(
    os.environ.get('JWT_PROXY') is not None,
    reason="Skipped because jwt proxy is in use"
)
@pytest.mark.parametrize("use_team", [False, True])
def test_dab_rbac_repository_owner_by_user_or_team(
    use_team,
    settings,
    ansible_config,
    galaxy_client,
    random_username
):

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)

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
    uid = me_ds['id']

    # find the role for repository owner ...
    rd = gc.get('_ui/v2/role_definitions/?name=galaxy.ansible_repository_owner')
    role_id = rd['results'][0]['id']

    # make a repository
    repo_name = random_username.replace('user_', 'repo_')
    repo_data = gc.post(
        'pulp/api/v3/repositories/ansible/ansible/',
        body=json.dumps({"name": repo_name})
    )
    repo_id = repo_data['pulp_href'].split('/')[-2]

    if not use_team:
        # assign the user role ...
        payload = {
            'user': uid,
            'role_definition': role_id,
            'content_type': 'galaxy.ansiblerepository',
            'object_id': repo_id,
        }
        gc.post('_ui/v2/role_user_assignments/', body=payload)

    else:
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
        team_id = team_data['id']

        # add the user to the team ...
        add_user_to_team(gc, userid=uid, teamid=team_id)

        # assign the user role ...
        payload = {
            'team': team_id,
            'role_definition': role_id,
            'content_type': 'galaxy.ansiblerepository',
            'object_id': repo_id,
        }
        gc.post('_ui/v2/role_team_assignments/', body=payload)

    # change the name ..
    change_task = ugc.patch(
        repo_data['pulp_href'],
        body=json.dumps({"name": repo_name + "foo"})
    )
    result = wait_for_task(ugc, change_task)
    assert result['state'] == 'completed'


# FIXME: unskip when https://issues.redhat.com/browse/AAP-32675 is merged
@pytest.mark.skip_in_gw
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.skipif(
    os.environ.get('JWT_PROXY') is not None,
    reason="Skipped because jwt proxy is in use"
)
@pytest.mark.parametrize("use_team", [False, True])
def test_dab_rbac_namespace_owner_by_user_or_team(
    use_team,
    settings,
    ansible_config,
    galaxy_client,
    random_namespace,
    random_username
):
    """
    Integration test to assert granting an object level namespace owner
    role definition to a user gives them the ability to upload, update
    and delete collections in the namespace and to alter the namespace.

    * Assumes that galaxy.collection_namespace_owner roledef exists
    * Assumes that galaxy.collection_namespace_owner lets the user change the
      namespace's company name
    * Assumes having galaxy.collection_namespace_owner implies a user can upload
    * Assumes having galaxy.collection_namespace_owner implies a user can delete
    * Assumes deletion is permissible even if the namespace owner may not be able
      to view a private repository that includes their collection.
    """

    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)

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
    uid = me_ds['id']

    # find the role for namespace owner ...
    rd = gc.get('_ui/v2/role_definitions/?name=galaxy.collection_namespace_owner')
    role_id = rd['results'][0]['id']

    if not use_team:
        # assign the user role ...
        payload = {
            'user': uid,
            'role_definition': role_id,
            'content_type': 'galaxy.namespace',
            'object_id': random_namespace['id'],
        }
        gc.post('_ui/v2/role_user_assignments/', body=payload)

    else:
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
        team_id = team_data['id']

        # add the user to the team ...
        add_user_to_team(gc, userid=uid, teamid=team_id)

        # assign the user role ...
        payload = {
            'team': team_id,
            'role_definition': role_id,
            'content_type': 'galaxy.namespace',
            'object_id': random_namespace['id'],
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

    # we need an artifact-like object for the set_certification function ..
    Artifact = namedtuple('Artifact', ['name', 'namespace', 'published', 'version'])

    # try to upload a collection as the user...
    import_result = upload_test_collection(
        ugc,
        namespace=random_namespace['name'],
        version='1.0.0'
    )
    artifact = Artifact(**import_result)
    ir2 = upload_test_collection(
        ugc,
        namespace=artifact.namespace,
        collection_name=artifact.name,
        version='1.0.1'
    )
    artifact2 = Artifact(**ir2)

    # certify both versions
    if settings.get('GALAXY_REQUIRE_CONTENT_APPROVAL') is True:
        set_certification(ansible_config(), gc, artifact)
        set_certification(ansible_config(), gc, artifact2)

    # try to delete the new version directly ...
    cv_url = (
        'v3/plugin/ansible/content/published/collections/index/'
        + f'{artifact2.namespace}/{artifact2.name}/versions/{artifact2.version}/'
    )
    del_task = ugc.delete(cv_url)
    result = wait_for_task(ugc, del_task)
    assert result['state'] == 'completed'

    # try to delete the collection as the user...
    collection_url = (
        'v3/plugin/ansible/content/published/collections/index/'
        + f'{artifact.namespace}/{artifact.name}/'
    )
    del_task = ugc.delete(collection_url)
    result = wait_for_task(ugc, del_task)
    assert result['state'] == 'completed'


@pytest.mark.deployment_standalone
@pytest.mark.skipif(
    os.environ.get('JWT_PROXY') is not None,
    reason="Skipped because jwt proxy is in use"
)
@pytest.mark.min_hub_version("4.10dev")
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
@pytest.mark.min_hub_version("4.10dev")
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


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
def test_dab_user_assignment_filtering_as_user(
    settings,
    galaxy_client,
    random_namespace,
    random_username,
):
    """
    Integration test to assert a user can be assigned as the owner
    of a namespace and then also be able to query their role assignments.

    * This assumes there is a galaxy.collection_namespace_owner roledef
      and that it has a content type defined.
    * This also assumes the role_user_assignments endpoint is user
      accessible and filterable.
    * The role_user_assignments endpoint behaves differently for
      evaluating a superuser vs a user for access.
    """
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("this test relies on local resource creation")

    gc = galaxy_client("admin", ignore_cache=True)

    # find the namespace owner roledef ...
    roledef = gc.get(
        '_ui/v2/role_definitions/?name=galaxy.collection_namespace_owner'
    )['results'][0]

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

    # assign the user to the namespace ...
    assignment = gc.post(
        '_ui/v2/role_user_assignments/',
        body=json.dumps({
            'user': uid,
            'role_definition': roledef['id'],
            'object_id': str(random_namespace['id']),
        })
    )

    # see if we can find the assignment through filtering as the user ...
    auth = {'username': random_username, 'password': 'redhat1234'}
    ugc = GalaxyClient(gc.galaxy_root, auth=auth)
    queryparams = [
        f"object_id={random_namespace['id']}",
        f"object_id={random_namespace['id']}&content_type__model=namespace",
    ]
    for qp in queryparams:
        resp = ugc.get(f'_ui/v2/role_user_assignments/?{qp}')
        assert resp['count'] == 1
        assert resp['results'][0]['id'] == assignment['id']


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.10dev")
@pytest.mark.skipif(
    os.environ.get('JWT_PROXY') is not None,
    reason="Skipped because jwt proxy is in use"
)
@pytest.mark.parametrize("use_team", [False, True])
def test_dab_rbac_ee_ownership_with_user_or_team(
    use_team,
    settings,
    galaxy_client,
    random_username,
):
    """
    Integration test to validate assigning a ee_namespace_owner
    roledefinition to a user or team will copy the roledef to the
    relevant pulp role assignment and reflect in the list_roles
    endpoint for the container namespace.

    * This does not check for functionality of the roledef.
    * This only validates the assignments.
    """
    if settings.get('ALLOW_LOCAL_RESOURCE_MANAGEMENT') is False:
        pytest.skip("this test relies on local resource creation")

    ROLE_NAME = 'galaxy.execution_environment_namespace_owner'
    registry_name = random_username.replace('user_', 'registry_')
    remote_name = random_username.replace('user_', 'remote_')

    gc = galaxy_client("admin", ignore_cache=True)

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

    if use_team:
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
        team_id = team_data['id']

        # add the user to the team ...
        add_user_to_team(gc, userid=uid, teamid=team_id)

        # what is the group name?
        group_name = team_data['group']['name']

    # make a registry ...
    registry_data = gc.post(
        "_ui/v1/execution-environments/registries/",
        body=json.dumps({
            "name": registry_name,
            "url": "https://quay.io/devspaces/ansible-creator-ee"
        })
    )
    registry_id = registry_data['pulp_href'].split('/')[-2]

    # make a remote with the registry ...
    gc.post(
        "_ui/v1/execution-environments/remotes/",
        body=json.dumps({
            "name": remote_name,
            "upstream_name": remote_name,
            "registry": registry_id,
            "include_tags": ["latest"],
            "exclude_tags": [],
        })
    )

    # find the "repository" ...
    repo_data = gc.get(f'v3/plugin/execution-environments/repositories/{remote_name}/')

    # what is the namespace data ..
    namespace_data = repo_data['namespace']

    # find the namespace owner roledef ...
    roledef = gc.get(
        f'_ui/v2/role_definitions/?name={ROLE_NAME}'
    )['results'][0]

    # make the roledef assignment ...
    if not use_team:
        assignment = gc.post(
            '_ui/v2/role_user_assignments/',
            body=json.dumps({
                'user': uid,
                'role_definition': roledef['id'],
                'object_id': namespace_data['id'],
            })
        )
    else:
        assignment = gc.post(
            '_ui/v2/role_team_assignments/',
            body=json.dumps({
                'team': team_id,
                'role_definition': roledef['id'],
                'object_id': namespace_data['id'],
            })
        )

    # is the user now listed in the namespace's list_roles endpoint?
    ns_roles = gc.get(namespace_data['pulp_href'] + 'list_roles/')
    ns_role_map = dict((x['role'], x) for x in ns_roles['roles'])
    if not use_team:
        assert random_username in ns_role_map[ROLE_NAME]['users']
    else:
        assert group_name in ns_role_map[ROLE_NAME]['groups']

    # delete the assignment
    try:
        gc.delete(assignment['url'])
    except Exception:
        pass
    ns_roles = gc.get(namespace_data['pulp_href'] + 'list_roles/')
    ns_role_map = dict((x['role'], x) for x in ns_roles['roles'])
    if not use_team:
        assert random_username not in ns_role_map[ROLE_NAME]['users']
    else:
        assert group_name not in ns_role_map[ROLE_NAME]['groups']
