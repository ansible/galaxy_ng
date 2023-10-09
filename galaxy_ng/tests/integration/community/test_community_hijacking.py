"""test_community.py - Tests related to the community featureset.
"""

import pytest

from ..utils import (
    get_client,
    SocialGithubClient,
    GithubAdminClient,
    cleanup_namespace,
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
def test_community_hijacking(ansible_config):

    default_cfg = extract_default_config(ansible_config)
    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )
    ga = GithubAdminClient()

    usermap = {
        'jctannerTESTME': {
            'uid': 2000,
            'login': 'jctannerTESTME',
            # 'email': 'jctannerTESTME@haxx.net',
            'email': '',
        },
        'drod0258X': {
            'uid': 2001,
            'login': 'drod0258X',
            # 'email': 'drod0258X@haxx.net',
            'email': ''
        }
    }

    # clean up all traces of these users ...
    for username, udata in usermap.items():
        ga.delete_user(uid=udata['uid'])
        for uname in [username, username.lower()]:
            cleanup_social_user(uname, ansible_config)
            cleanup_namespace(uname, api_client=admin_client)
            ga.delete_user(login=uname)

    # create api client configs
    for username, udata in usermap.items():
        ucfg = ga.create_user(**udata)
        ucfg.update(default_cfg)
        ucfg['username'] = username
        usermap[username]['cfg'] = ucfg

    # make clients and login
    for username, udata in usermap.items():
        sclient = SocialGithubClient(config=udata['cfg'])
        usermap[username]['client'] = sclient
        usermap[username]['client'].login()

    # force logout
    for username, udata in usermap.items():
        usermap[username]['client'].logout()

    # force login
    for username, udata in usermap.items():
        usermap[username]['client'].login()

    # check me
    for username, udata in usermap.items():
        me_rr = usermap[username]['client'].get('_ui/v1/me/')
        usermap[username]['me'] = me_rr.json()['username']

    # ensure no shenanigens happened ...
    for username, udata in usermap.items():
        assert udata['me'] == username
