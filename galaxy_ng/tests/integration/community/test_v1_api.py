"""test_community.py - Tests related to the community featureset.
"""

import pytest

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
