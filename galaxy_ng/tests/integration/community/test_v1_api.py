"""test_community.py - Tests related to the community featureset.
"""

import pytest

from ansible.errors import AnsibleError

from ..utils import (
    ansible_galaxy,
    get_client,
    SocialGithubClient,
)
from ..utils.legacy import (
    cleanup_social_user,
)

pytestmark = pytest.mark.qa  # noqa: F821


def extract_default_config(ansible_config):
    base_cfg = ansible_config('github_user_1')
    cfg = {}
    cfg['token'] = None
    cfg['url'] = base_cfg.get('url')
    cfg['auth_url'] = base_cfg.get('auth_url')
    cfg['github_url'] = base_cfg.get('github_url')
    cfg['github_api_url'] = base_cfg.get('github_api_url')
    return cfg


@pytest.mark.deployment_community
def test_v1_owner_username_filter_is_case_insensitive(ansible_config):
    """" Tests if v1 sync accepts a user&limit arg """

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True
    )

    github_user = 'jctannerTEST'
    github_repo = 'role1'
    cleanup_social_user(github_user, ansible_config)

    user_cfg = extract_default_config(ansible_config)
    user_cfg['username'] = github_user
    user_cfg['password'] = 'redhat'

    # Login with the user first to create the v1+v3 namespaces
    with SocialGithubClient(config=user_cfg) as client:
        me = client.get('_ui/v1/me/')
        assert me.json()['username'] == github_user

    # Run the import
    import_pid = ansible_galaxy(
        f"role import {github_user} {github_repo}",
        ansible_config=config,
        token=None,
        force_token=False,
        cleanup=False,
        check_retcode=False
    )
    assert import_pid.returncode == 0

    # verify filtering in the way that the CLI does it
    resp = api_client(f'/api/v1/roles/?owner__username={github_user}')
    assert resp['count'] == 1
    assert resp['results'][0]['username'] == github_user
    roleid = resp['results'][0]['id']

    # verify filtering with the username as lowercase ...
    resp2 = api_client(f'/api/v1/roles/?owner__username={github_user.lower()}')
    assert resp2['count'] == 1
    assert resp2['results'][0]['username'] == github_user
    roleid2 = resp2['results'][0]['id']

    # roleids should match
    assert roleid == roleid2

    # cleanup
    cleanup_social_user(github_user, ansible_config)


@pytest.mark.deployment_community
def test_v1_users_filter(ansible_config):
    """" Tests v1 users filter works as expected """

    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True
    )

    github_user = 'jctannerTEST'
    # github_repo = 'role1'
    cleanup_social_user(github_user, ansible_config)

    user_cfg = extract_default_config(ansible_config)
    user_cfg['username'] = github_user
    user_cfg['password'] = 'redhat'

    # Login with the user first to create the v1+v3 namespaces
    with SocialGithubClient(config=user_cfg) as client:
        me = client.get('_ui/v1/me/')
        assert me.json()['username'] == github_user

    resp = api_client('/api/v1/users/')

    assert len(resp["results"]) > 0

    resp = api_client(f'/api/v1/users/?username={github_user}')

    assert resp["count"] == 1
    assert resp["results"][0]["username"] == github_user

    resp = api_client('/api/v1/users/?username=user_should_not_exist')
    assert resp["count"] == 0

    cleanup_social_user(github_user, ansible_config)


@pytest.mark.deployment_community
def test_custom_browsable_format(ansible_config):
    """" Test endpoints works with enabled browsable api """

    # test as a admin
    config = ansible_config("admin")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True,
    )

    resp = api_client("v1/namespaces/")
    assert isinstance(resp, dict)
    assert "results" in resp

    resp = api_client("v1/namespaces?format=json")
    assert isinstance(resp, dict)
    assert "results" in resp

    with pytest.raises(AnsibleError) as html:
        api_client("v1/namespaces/", headers={"Accept": "text/html"})
    assert not isinstance(html.value, dict)
    assert "results" in str(html.value)

    # test as a basic user
    config = ansible_config("basic_user")
    api_client = get_client(
        config=config,
        request_token=False,
        require_auth=True,
    )

    resp = api_client("v1/namespaces/")
    assert isinstance(resp, dict)
    assert "results" in resp

    resp = api_client("v1/namespaces?format=json")
    assert isinstance(resp, dict)
    assert "results" in resp

    with pytest.raises(AnsibleError) as html:
        api_client("v1/namespaces/", headers={"Accept": "text/html"})
    assert not isinstance(html.value, dict)
    assert "results" in str(html.value)
