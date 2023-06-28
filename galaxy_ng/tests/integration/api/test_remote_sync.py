from datetime import datetime

import pytest
from jsonschema import validate as validate_json

from ansible.galaxy.api import GalaxyError

from ..schemas import (
    schema_objectlist,
    schema_task,
)
from ..utils import get_client, wait_for_task

REQUIREMENTS_FILE = "collections:\n  - name: newswangerd.collection_demo\n    version: 1.0.11"


# /api/automation-hub/content/community/v3/sync/config/
# /api/automation-hub/content/community/v3/sync/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
def test_api_ui_v1_remote_sync(ansible_config):

    cfg = ansible_config("admin")
    api_client = get_client(cfg, request_token=True, require_auth=True)

    # get the remotes
    resp = api_client("_ui/v1/remotes/", args={}, method="GET")
    validate_json(instance=resp, schema=schema_objectlist)

    # update the community remote
    cfg = ansible_config('admin')
    api_prefix = cfg.get("api_prefix").rstrip("/")
    payload = {
        'url': 'https://beta-galaxy.ansible.com/api/',
        'auth_url': None,
        'token': None,
        'policy': 'immediate',
        'requirements_file': REQUIREMENTS_FILE,
        'created_at': str(datetime.now()),
        'updated_at': str(datetime.now()),
        'username': None,
        'password': None,
        'tls_validation': False,
        'client_key': None,
        'client_cert': None,
        'ca_cert': None,
        'download_concurrency': 10,
        'proxy_url': None,
        'proxy_username': None,
        'proxy_password': None,
        'rate_limit': 8,
        'signed_only': False,
    }
    resp = api_client("content/community/v3/sync/config/", args=payload, method="PUT")

    # verify change
    assert resp['requirements_file'] == REQUIREMENTS_FILE

    # sync
    resp = api_client("content/community/v3/sync/", args=payload, method="POST")
    task = {'task': f'{api_prefix}/pulp/api/v3/tasks/{resp["task"]}/'}
    validate_json(instance=task, schema=schema_task)
    resp = wait_for_task(api_client, task)

    try:
        if "Internal Server Error" in resp["error"]["description"]:
            pytest.skip("Server error on https://beta-galaxy.ansible.com/. Skipping test.")
    except TypeError:
        pass

    # search collections for synced collection
    resp = api_client(
        f"{api_prefix}/_ui/v1/repo/community/?namespace=newswangerd&name=collection_demo",
        args={},
        method="GET"
    )

    ds = resp['data']
    assert len(ds) == 1
    assert ds[0]['namespace']['name'] == 'newswangerd'
    assert ds[0]['name'] == 'collection_demo'


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_sync_community_with_no_requirements_file(ansible_config):
    cfg = ansible_config("admin")
    api_client = get_client(cfg, request_token=True, require_auth=True)

    remote = api_client("pulp/api/v3/remotes/ansible/collection/?name=community")["results"][0]
    resp = api_client(
        remote["pulp_href"],
        method="PATCH",
        args={
            "requirements_file": None,
            "url": "https://beta-galaxy.ansible.com/api/",
        }
    )
    wait_for_task(api_client, resp)

    repo = api_client("pulp/api/v3/repositories/ansible/ansible/?name=community")["results"][0]

    try:
        api_client(f'{repo["pulp_href"]}sync/', method="POST")
        # This API call should fail
        assert False
    except GalaxyError as ge:
        assert ge.http_code == 400
        # galaxy kit can't parse pulp error messages, so the contents of the error
        # message can't be verified.
        # assert "requirements_file" in ge.message
