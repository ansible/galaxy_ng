"""test_community.py - Tests related to the community featureset.
"""

import pytest

from ..utils import (
    get_client,
)
from ..utils.legacy import (
    cleanup_social_user,
    LegacyRoleGitRepoBuilder,
    wait_for_v1_task
)

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.parametrize(
    'spec',
    [
        {
            'namespace': 'foo',
            'name': 'bar',
            'github_user': 'foo',
            'github_repo': 'bar',
            'meta_namespace': None,
            'meta_name': None,
            'alternate_namespace_name': 'foo',
            'alternate_role_name': 'bar',
        },
        {
            'namespace': 'jim32',
            'name': 'bob32',
            'github_user': 'jim',
            'github_repo': 'bob',
            'meta_namespace': 'jim32',
            'meta_name': 'bob32',
            'alternate_namespace_name': None,
            'alternate_role_name': None,
        }

    ]
)
@pytest.mark.deployment_community
def test_role_import_overrides(ansible_config, spec):
    """" Validate setting namespace in meta/main.yml does the right thing """

    admin_config = ansible_config("admin")
    admin_client = get_client(
        config=admin_config,
        request_token=False,
        require_auth=True
    )

    # all required namespaces ...
    ns_names = [
        spec['namespace'],
        spec['github_user'],
        spec['alternate_namespace_name'],
        spec['meta_namespace']
    ]
    ns_names = sorted(set([x for x in ns_names if x]))

    # cleanup
    for ns_name in ns_names:
        cleanup_social_user(ns_name, ansible_config)
        try:
            admin_client(f'/api/v3/namespaces/{ns_name}/', method='DELETE')
        except Exception:
            pass

    # make the namespace(s)
    for ns_name in ns_names:
        v1 = admin_client('/api/v1/namespaces/', method='POST', args={'name': ns_name})
        v3 = admin_client('/api/v3/namespaces/', method='POST', args={'name': ns_name})
        admin_client(
            f'/api/v1/namespaces/{v1["id"]}/providers/', method='POST', args={'id': v3['id']}
        )

    # make a local git repo
    builder_kwargs = {
        'namespace': spec['namespace'],
        'name': spec['name'],
        'meta_namespace': spec['meta_namespace'],
        'meta_name': spec['meta_name'],
    }
    lr = LegacyRoleGitRepoBuilder(**builder_kwargs)

    # run the import
    payload = {'alternate_clone_url': lr.role_dir}
    for key in ['github_user', 'github_repo', 'alternate_namespace_name', 'alternate_role_name']:
        if spec.get(key):
            payload[key] = spec[key]
    resp = admin_client('/api/v1/imports/', method='POST', args=payload)
    task_id = resp['results'][0]['id']
    result = wait_for_v1_task(task_id=task_id, api_client=admin_client)
    assert result['results'][0]['state'] == 'SUCCESS'

    # find the role and check it's attributes ...
    roles_search = admin_client(f'/api/v1/roles/?namespace={spec["namespace"]}&name={spec["name"]}')
    assert roles_search['count'] == 1
    assert roles_search['results'][0]['summary_fields']['namespace']['name'] == spec['namespace']
    assert roles_search['results'][0]['name'] == spec['name']
    assert roles_search['results'][0]['github_user'] == spec['github_user']
    assert roles_search['results'][0]['github_repo'] == spec['github_repo']
