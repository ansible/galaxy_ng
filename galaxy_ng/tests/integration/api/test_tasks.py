import pytest

from ..utils import get_client, UIClient


@pytest.mark.pulp_api
@pytest.mark.standalone_only
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
