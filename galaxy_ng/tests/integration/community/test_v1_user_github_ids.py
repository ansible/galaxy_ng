"""test_community.py - Tests related to the community featureset.
"""

import pytest

from ..utils import (
    SocialGithubClient,
    GithubAdminClient,
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
def test_v1_user_github_ids(ansible_config):
    """" The github_id should show up in the v1 user serializer """

    for x in range(0, 10):

        github_user = 'deleteme' + str(x)
        cleanup_social_user(github_user, ansible_config)

        user_cfg = extract_default_config(ansible_config)
        user_cfg['username'] = github_user
        user_cfg['password'] = 'redhat'

        # delete and recreate the github user ...
        ga = GithubAdminClient()
        try:
            ga.delete_user(login=github_user)
        except Exception:
            pass
        gdata = ga.create_user(
            login=github_user,
            password='redhat',
            email=f'{github_user}@bar.com'
        )

        # Login with the user first to create the v1+v3 namespaces
        with SocialGithubClient(config=user_cfg) as client:
            me = client.get('_ui/v1/me/')
            assert me.json()['username'] == github_user
            uid = me.json()['id']

            urr = client.get(f'v1/users/{uid}/')
            udata = urr.json()
            assert udata['github_id'] == gdata['id']
