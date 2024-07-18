import pytest

from ..utils import UIClient
from ..utils.iqe_utils import aap_gateway
from ..utils.tools import generate_random_string

REQUIREMENTS_YAML = """
collections:
  - name: newswangerd.collection_demo
"""


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_logging_cid_value_in_task(galaxy_client, ansible_config):
    gc = galaxy_client("admin")
    config = ansible_config("admin")
    ans_repo = gc.get(
        "pulp/api/v3/repositories/ansible/ansible/?name=rh-certified"
    )['results'][0]

    # extract pulp_id from pulp_href
    pulp_id = ans_repo["pulp_href"].split('/ansible/ansible/')[1].rstrip('/')

    # use UIClient to get Correlation-ID from req headers
    with UIClient(config=config) as uic:
        sync_req = uic.post(
            f"pulp/api/v3/repositories/ansible/ansible/{pulp_id}/sync/",
            payload={})

    sync_task = sync_req.json()["task"]
    logging_cid = gc.get(sync_task)["logging_cid"]

    assert logging_cid != ""
    assert sync_req.headers["Correlation-ID"] == logging_cid


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.skipif(not aap_gateway(), reason="This test only runs if AAP Gateway is deployed")
def test_gateway_logging_cid_value_in_task(galaxy_client):
    gc = galaxy_client("admin")
    ans_repo = gc.get(
        "pulp/api/v3/repositories/ansible/ansible/?name=rh-certified"
    )['results'][0]

    # extract pulp_id from pulp_href
    pulp_id = ans_repo["pulp_href"].split('/ansible/ansible/')[1].rstrip('/')
    sync_req = gc.post(
        f"pulp/api/v3/repositories/ansible/ansible/{pulp_id}/sync/",
        body={})

    correlation_id = gc.response.headers["Correlation-ID"]

    sync_task = sync_req["task"]
    logging_cid = gc.get(sync_task)["logging_cid"]

    assert logging_cid != ""
    assert correlation_id == logging_cid


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_task_delete(galaxy_client):
    gc = galaxy_client("admin")

    # Create a remote and repo to use for sync
    remote = gc.post("pulp/api/v3/remotes/ansible/collection/", body={
        "name": generate_random_string(),
        "url": "https://galaxy.ansible.com",
        "requirements_file": REQUIREMENTS_YAML
    })

    repo = gc.post("pulp/api/v3/repositories/ansible/ansible/", body={
        "name": f"repo-test-{generate_random_string()}",
        "remote": remote["pulp_href"]
    })

    '''
    cleanup = PulpObjectBase(api_client)
    cleanup.cleanup_hrefs = [
        remote["pulp_href"],
        repo["pulp_href"]
    ]
    '''

    # Launch a sync task, since that seems to be the only that can keep the tasking
    # system busy long enough to cancel a task
    task = gc.post(repo["pulp_href"] + "sync/", body={
        "optimize": False
    })["task"]

    # cancel the task
    gc.patch(task, body={"state": "canceled"})

    # verify the task's status
    task = gc.get(task)
    assert task["state"] in ["canceled", "canceling"]
