"""test_community.py - Tests related to the community featureset.
"""

import pytest

from ..utils import (
    ansible_galaxy,
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
def test_role_import_exceptions(ansible_config):
    """" Exceptions should end up in the client facing logs """

    config = ansible_config("admin")
    github_user = 'jctanner'
    github_repo = 'busted-role'
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
    ga.create_user(login=github_user, password='redhat', email='jctanner.foo@bar.com')

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

    # core always exits zero...
    # https://github.com/ansible/ansible/issues/82175
    assert import_pid.returncode == 0

    stdout = import_pid.stdout.decode('utf-8')
    assert 'Traceback (most recent call last):' in stdout
    assert 'galaxy_importer.exceptions.LegacyRoleSchemaError' in stdout

    # cleanup
    cleanup_social_user(github_user, ansible_config)
