import pytest

from ..utils import get_client, UIClient, PulpObjectBase
from ..utils.tools import generate_random_string

REQUIREMENTS_YAML = """
collections:
  - name: newswangerd.collection_demo
"""


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_logging_cid_value_in_task(ansible_config):
    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(config, request_token=True)

    ans_repo = api_client(
        f"{api_prefix}/pulp/api/v3/repositories/ansible/ansible/?name=rh-certified",
        method="GET"
    )['results'][0]

    # extract pulp_id from pulp_href
    pulp_id = ans_repo["pulp_href"].split('/ansible/ansible/')[1].rstrip('/')

    # use UIClient to get Correlation-ID from req headers
    with UIClient(config=config) as uic:
        sync_req = uic.post(
            f"pulp/api/v3/repositories/ansible/ansible/{pulp_id}/sync/",
            payload={})

    sync_task = sync_req.json()["task"]
    logging_cid = api_client(sync_task)["logging_cid"]

    assert logging_cid != ""
    assert sync_req.headers["Correlation-ID"] == logging_cid


@pytest.mark.pulp_api
@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
def test_task_delete(ansible_config):
    config = ansible_config("admin")
    api_client = get_client(config, request_token=True)

    # Create a remote and repo to use for sync
    remote = api_client("pulp/api/v3/remotes/ansible/collection/", method="POST", args={
        "name": generate_random_string(),
        "url": "https://galaxy.ansible.com",
        "requirements_file": REQUIREMENTS_YAML
    })

    repo = api_client("pulp/api/v3/repositories/ansible/ansible/", method="POST", args={
        "name": generate_random_string(),
        "remote": remote["pulp_href"]
    })

    cleanup = PulpObjectBase(api_client)
    cleanup.cleanup_hrefs = [
        remote["pulp_href"],
        repo["pulp_href"]
    ]

    # Launch a sync task, since that seems to be the only that can keep the tasking
    # system busy long enough to cancel a task
    task = api_client(repo["pulp_href"] + "/sync/", method="POST", args={
        "optimize": False
    })["task"]

    # cancel the task
    api_client(task, method="PATCH", args={"state": "canceled"})

    # verify the task's status
    task = api_client(task)
    assert task["state"] in ["canceled", "canceling"]
