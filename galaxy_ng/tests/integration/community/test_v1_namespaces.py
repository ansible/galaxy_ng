"""test_community.py - Tests related to the community featureset.
"""

import pytest

from ..utils import (
    ansible_galaxy,
    SocialGithubClient,
    get_client,
    generate_unused_namespace,
)

from ..utils.legacy import cleanup_social_user
from ..utils.legacy import generate_unused_legacy_namespace

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_community
def test_social_auth_creates_v3_namespace_as_v1_provider(ansible_config):

    github_user = 'jctannerTEST'
    github_repo = 'role1'
    cleanup_social_user(github_user, ansible_config)
    cleanup_social_user(github_user.lower(), ansible_config)

    cfg = ansible_config(github_user)
    with SocialGithubClient(config=cfg) as client:

        # check the v1 namespace's provider namespace
        resp = client.get(f'v1/namespaces/?name={github_user}')
        res = resp.json()
        v1_namespace = res['results'][0]
        provider_namespace = v1_namespace['summary_fields']['provider_namespaces'][0]
        assert provider_namespace['name'] == github_user.lower()

        # import a role
        token = client.get_hub_token()
        import_pid = ansible_galaxy(
            f"role import {github_user} {github_repo}",
            ansible_config=cfg,
            token=token,
            force_token=True,
            cleanup=False,
            check_retcode=False
        )
        assert import_pid.returncode == 0

        # check the role's provider namespace
        resp = client.get(f'v1/roles/?owner__username={github_user}&name={github_repo}')
        res = resp.json()
        role = res['results'][0]
        provider_namespace = role['summary_fields']['provider_namespace']
        assert provider_namespace['name'] == github_user.lower()

        # set the provider namespace's avatar url
        # PUT https://galaxy-dev.ansible.com/api/_ui/v1/my-namespaces/jctannertest/
        provider_name = provider_namespace['name']
        avatar_url = (
            'https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/'
            + 'NASA_logo.svg/918px-NASA_logo.svg.png'
        )
        rr = client.put(
            f'_ui/v1/my-namespaces/{provider_name}/',
            data={
                'name': provider_name,
                'avatar_url': avatar_url
            }
        )
        assert rr.status_code == 200

        # check the role's new avatar url ...
        resp = client.get(f'v1/roles/?owner__username={github_user}&name={github_repo}')
        res = resp.json()
        role = res['results'][0]
        assert role['summary_fields']['namespace']['avatar_url'] == avatar_url

        # check the legacynamespace's avatar url ...
        resp = client.get(f'v1/namespaces/?name={github_user}')
        res = resp.json()
        assert res['results'][0]['avatar_url'] == avatar_url


@pytest.mark.deployment_community
def test_v1_namespace_provider_filter(ansible_config):

    admin_config = ansible_config('admin')
    admin_client = get_client(config=admin_config, request_token=False, require_auth=True)

    # 2 v1 namespaces
    v1_a_name = generate_unused_legacy_namespace(admin_client)
    v1_a = admin_client('/api/v1/namespaces/', method='POST', args={'name': v1_a_name})
    v1_a_id = v1_a['id']
    v1_b_name = generate_unused_legacy_namespace(admin_client)
    v1_b = admin_client('/api/v1/namespaces/', method='POST', args={'name': v1_b_name})
    v1_b_id = v1_b['id']

    # make 1 v3 namespace
    v3_a_name = generate_unused_namespace(admin_client)
    v3_a = admin_client(
        '/api/v3/namespaces/', method='POST', args={'name': v3_a_name, 'groups': []}
    )
    v3_a_id = v3_a['id']
    v3_b_name = generate_unused_namespace(admin_client)
    v3_b = admin_client(
        '/api/v3/namespaces/', method='POST', args={'name': v3_b_name, 'groups': []}
    )
    v3_b_id = v3_b['id']

    # bind v1_a to v3 and v1_b to v3_b
    admin_client(f'/api/v1/namespaces/{v1_a_id}/providers/', method='POST', args={'id': v3_a_id})
    admin_client(f'/api/v1/namespaces/{v1_b_id}/providers/', method='POST', args={'id': v3_b_id})

    # check the filter ..
    resp_a = admin_client(f'/api/v1/namespaces/?provider={v3_a_name}')
    resp_b = admin_client(f'/api/v1/namespaces/?provider={v3_b_name}')

    assert resp_a['count'] == 1
    assert resp_a['results'][0]['id'] == v1_a_id, resp_a

    assert resp_b['count'] == 1
    assert resp_b['results'][0]['id'] == v1_b_id, resp_b
