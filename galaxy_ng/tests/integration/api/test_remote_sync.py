from datetime import datetime

import pytest
from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
    schema_task,
)
from ..utils import get_client, wait_for_task

REQUIREMENTS_FILE = "collections:\n  - name: newswangerd.collection_demo\n    version: 1.0.11"


# /api/automation-hub/content/community/v3/sync/config/
# /api/automation-hub/content/community/v3/sync/
@pytest.mark.standalone_only
def test_api_ui_v1_remote_sync(ansible_config):

    cfg = ansible_config("admin")
    api_client = get_client(cfg, request_token=True, require_auth=True)

    # get the remotes
    resp = api_client("_ui/v1/remotes/", args={}, method="GET")
    validate_json(instance=resp, schema=schema_objectlist)

    # update the community remote
    cfg = ansible_config('admin')
    payload = {
        'url': 'https://galaxy.ansible.com/api/',
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
    task = {'task': f'/api/automation-hub/pulp/api/v3/tasks/{resp["task"]}/'}
    validate_json(instance=task, schema=schema_task)
    resp = wait_for_task(api_client, task)

    # search collections for synced collection
    cfg = ansible_config('admin')
    resp = api_client(
        "_ui/v1/repo/community/?namespace=newswangerd&name=collection_demo",
        args={},
        method="GET"
    )
    ds = resp['data']
    assert len(ds) == 1
    assert ds[0]['namespace']['name'] == 'newswangerd'
    assert ds[0]['name'] == 'collection_demo'
