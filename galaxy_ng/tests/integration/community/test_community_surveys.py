import copy
import json
import pytest
import random
import string

from ..utils import (
    get_client,
    SocialGithubClient,
    GithubAdminClient,
    cleanup_namespace,
)
from ..utils.legacy import (
    cleanup_social_user,
    wait_for_v1_task,
)


pytestmark = pytest.mark.qa  # noqa: F821


SURVEY_FIELDS = [
    'docs',
    'ease_of_use',
    'does_what_it_says',
    'works_as_is',
    'used_in_production'
]


def extract_default_config(ansible_config):
    base_cfg = ansible_config('github_user_1')
    cfg = {}
    cfg['token'] = None
    cfg['url'] = base_cfg.get('url')
    cfg['auth_url'] = base_cfg.get('auth_url')
    cfg['github_url'] = base_cfg.get('github_url')
    cfg['github_api_url'] = base_cfg.get('github_api_url')
    return cfg


@pytest.fixture()
def default_config(ansible_config):
    yield extract_default_config(ansible_config)


@pytest.fixture
def imported_role(ansible_config):
    github_user = 'jctannerTEST'
    github_repo = 'role1'
    cleanup_social_user(github_user, ansible_config)
    cleanup_social_user(github_user.lower(), ansible_config)

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # make the legacy namespace
    ns_payload = {
        'name': github_user
    }
    resp = admin_client('/api/v1/namespaces/', method='POST', args=ns_payload)
    assert resp['name'] == github_user, resp
    assert not resp['summary_fields']['owners'], resp
    assert not resp['summary_fields']['provider_namespaces'], resp
    v1_id = resp['id']

    # make the v3 namespace
    v3_payload = {
        'name': github_user.lower(),
        'groups': [],
    }
    resp = admin_client('/api/_ui/v1/namespaces/', method='POST', args=v3_payload)
    assert resp['name'] == github_user.lower(), resp
    v3_id = resp['id']

    # bind the v3 namespace to the v1 namespace
    v3_bind = {
        'id': v3_id
    }
    admin_client(f'/api/v1/namespaces/{v1_id}/providers/', method='POST', args=v3_bind)

    # do an import with the admin ...
    payload = {
        'github_repo': github_repo,
        'github_user': github_user,
    }
    resp = admin_client('/api/v1/imports/', method='POST', args=payload)
    task_id = resp['results'][0]['id']
    res = wait_for_v1_task(task_id=task_id, api_client=admin_client, check=False)

    # get the role ...
    role_qs = admin_client(f'/api/v1/roles/?owner__username={github_user}&name={github_repo}')
    role_ds = role_qs['results'][0]

    yield role_ds
    

@pytest.mark.deployment_community
def test_community_role_survey(ansible_config, default_config, imported_role):
    roleid = imported_role['id']

    ga = GithubAdminClient()

    possible_values = [None] + list(range(0,6))
    user_survey_map = {
        'bob1': dict((x, random.choice(possible_values)) for x in SURVEY_FIELDS),
        'bob2': dict((x, random.choice(possible_values)) for x in SURVEY_FIELDS),
        'bob3': dict((x, random.choice(possible_values)) for x in SURVEY_FIELDS),
    }

    for username, payload in user_survey_map.items():
        print(username)
        cleanup_social_user(username, ansible_config)
        ga.delete_user(login=username)
        gcfg = ga.create_user(
            login=username,
            password='foobar1234',
            email=username + '@noreply.github.com'
        )
        gcfg['username'] = username
        gcfg.update(default_config)

        with SocialGithubClient(config=gcfg) as sclient:
            rkwargs = {
                'absolute_url': f'/api/v3/surveys/roles/{roleid}/',
                'data': payload,
            }
            resp = sclient.post(**rkwargs)
            import epdb; epdb.st()
            print(resp)

    import epdb; epdb.st()