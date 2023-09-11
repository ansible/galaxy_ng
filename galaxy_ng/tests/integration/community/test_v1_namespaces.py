"""test_community.py - Tests related to the community featureset.
"""

import json
import pytest

from urllib.parse import urlparse

from ..utils import (
    ansible_galaxy,
    build_collection,
    get_client,
    SocialGithubClient,
    create_user,
)
from ..utils.legacy import (
    clean_all_roles,
    cleanup_social_user,
    wait_for_v1_task,
)

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)


pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.deployment_community
def test_social_auth_creates_v3_namespace_new(ansible_config):

    github_user = 'jctannerTEST'
    github_repo = 'role1'
    cleanup_social_user(github_user, ansible_config)

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

        import epdb; epdb.st()
        print('done')
