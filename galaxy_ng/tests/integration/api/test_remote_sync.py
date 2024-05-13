from datetime import datetime

import pytest
from jsonschema import validate as validate_json

from galaxykit.utils import wait_for_task, GalaxyClientError
from ..schemas import (
    schema_objectlist,
    schema_task,
)

REQUIREMENTS_FILE = "collections:\n  - name: newswangerd.collection_demo\n    version: 1.0.11"


# /api/automation-hub/content/community/v3/sync/config/
# /api/automation-hub/content/community/v3/sync/
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.6dev")
def test_api_ui_v1_remote_sync(galaxy_client):

    gc = galaxy_client("admin")
    # get the remotes
    resp = gc.get("_ui/v1/remotes/")
    validate_json(instance=resp, schema=schema_objectlist)
    # update the community remote
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
    resp = gc.put("content/community/v3/sync/config/", body=payload)

    # verify change
    assert resp['requirements_file'] == REQUIREMENTS_FILE

    # sync
    resp = gc.post("content/community/v3/sync/", body=payload)
    task = {'task': f'pulp/api/v3/tasks/{resp["task"]}/'}
    validate_json(instance=task, schema=schema_task)
    resp = wait_for_task(gc, task)

    try:
        if "Internal Server Error" in resp["error"]["description"]:
            pytest.skip("Server error on https://beta-galaxy.ansible.com/. Skipping test.")
    except TypeError:
        pass

    # search collections for synced collection
    resp = gc.get("_ui/v1/repo/community/?namespace=newswangerd&name=collection_demo")

    ds = resp['data']
    assert len(ds) == 1
    assert ds[0]['namespace']['name'] == 'newswangerd'
    assert ds[0]['name'] == 'collection_demo'


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_sync_community_with_no_requirements_file(galaxy_client):
    gc = galaxy_client("admin")
    remote = gc.get("pulp/api/v3/remotes/ansible/collection/?name=community")["results"][0]
    resp = gc.patch(
        remote["pulp_href"],
        body={
            "requirements_file": None,
            "url": "https://beta-galaxy.ansible.com/api/",
        }
    )
    wait_for_task(gc, resp)

    repo = gc.get("pulp/api/v3/repositories/ansible/ansible/?name=community")["results"][0]
    try:
        gc.post(f'{repo["pulp_href"]}sync/', body={})
        # This API call should fail
        assert False
    except GalaxyClientError as ge:
        assert ge.response.status_code == 400
        # galaxy kit can't parse pulp error messages, so the contents of the error
        # message can't be verified.
        # assert "requirements_file" in ge.message
