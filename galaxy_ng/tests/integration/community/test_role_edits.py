import pytest

# from ..utils import ansible_galaxy, get_client, SocialGithubClient
from ..utils import ansible_galaxy, get_client
from ..utils.legacy import clean_all_roles, cleanup_social_user


@pytest.mark.deployment_community
def test_community_legacy_role_edit(ansible_config):

    # namespace_name = painless
    # github_user = painless-software
    # github_repository = ansible-role-software
    # role_name = software
    # install fqn = painless.software
    # github_branch = main

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    namespace_v3name = 'jctannertest'
    namespace_v1name = 'jctannerTEST'
    github_user = 'jctannerTEST'
    github_repo = 'role1'
    role_name = 'role1'
    branch = 'master'

    # cleanup
    clean_all_roles(ansible_config)
    cleanup_social_user(namespace_v3name, ansible_config)
    cleanup_social_user(namespace_v1name, ansible_config)

    # creat the v3 namespace
    v3_ns = admin_client(
        '/api/_ui/v1/namespaces/', method='POST', args={'name': namespace_v3name, 'groups': []}
    )
    assert v3_ns['name'] == namespace_v3name, v3_ns

    # make the legacy ns
    v1_ns = admin_client('/api/v1/namespaces/', method='POST', args={'name': namespace_v1name})
    assert v1_ns['name'] == namespace_v1name, v1_ns

    # bind the v3 namespace to the v1 namespace
    v3_bind = {
        'id': v3_ns['id']
    }
    admin_client(f"/api/v1/namespaces/{v1_ns['id']}/providers/", method='POST', args=v3_bind)

    # import jctanerTEST role1
    pid = ansible_galaxy(
        f"role import {github_user} {github_repo} --branch={branch}",
        ansible_config=admin_config,
        force_token=True,
        cleanup=False,
        check_retcode=False
    )
    assert pid.returncode == 0, pid.stdout.decode('utf-8')

    # find the new role ...
    resp = admin_client(f'/api/v1/roles/?owner__username={namespace_v1name}&name={role_name}')
    assert resp['count'] == 1
    role = resp['results'][0]
    assert role['summary_fields']['namespace']['name'] == namespace_v1name
    assert role['summary_fields']['provider_namespace']['name'] == namespace_v3name
    assert role['name'] == role_name
    assert role['github_user'] == github_user
    assert role['github_repo'] == github_repo
    assert role['github_branch'] == branch

    role_id = role['id']

    # change the branch ...
    admin_client(
        f'/api/v1/roles/{role_id}/',
        method='PUT',
        args={'github_branch': 'fakebranch'}
    )
    newds = admin_client(f'/api/v1/roles/{role_id}/')
    assert newds['github_branch'] == 'fakebranch'

    # change the github_user ...
    admin_client(
        f'/api/v1/roles/{role_id}/',
        method='PUT',
        args={'github_user': 'fakeuser'}
    )
    newds = admin_client(f'/api/v1/roles/{role_id}/')
    assert newds['github_user'] == 'fakeuser'

    # change the github_repo ...
    admin_client(
        f'/api/v1/roles/{role_id}/',
        method='PUT',
        args={'github_repo': 'fakerepo'}
    )
    newds = admin_client(f'/api/v1/roles/{role_id}/')
    assert newds['github_repo'] == 'fakerepo'

    # change the repository.name ...
    admin_client(
        f'/api/v1/roles/{role_id}/',
        method='PUT',
        args={
            'repository': {
                'name': 'foorepo'
            }
        }
    )
    newds = admin_client(f'/api/v1/roles/{role_id}/')
    assert newds['summary_fields']['repository']['name'] == 'foorepo'

    # change the repository.original_name ...
    admin_client(
        f'/api/v1/roles/{role_id}/',
        method='PUT',
        args={
            'repository': {
                'original_name': 'foorepo_old'
            }
        }
    )
    newds = admin_client(f'/api/v1/roles/{role_id}/')
    assert newds['summary_fields']['repository']['original_name'] == 'foorepo_old'

    # cleanup the role ...
    try:
        admin_client(f'/api/v1/roles/{role_id}/', method='DELETE')
    except Exception:
        pass
