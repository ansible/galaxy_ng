import logging

import pytest

from galaxykit import GalaxyClient
from galaxykit.collections import upload_artifact, delete_collection
from pkg_resources import parse_version

from galaxykit.utils import wait_for_task as gk_wait_for_task
from ..utils import wait_for_task, get_client, set_certification
from orionutils.generator import build_collection
from ..utils.iqe_utils import (
    is_sync_testing,
    get_all_collections,
    retrieve_collection, get_ansible_config, get_galaxy_client, get_hub_version,
    has_old_credentials,
)
from ..utils.tools import generate_random_artifact_version, uuid4

pytestmark = pytest.mark.qa  # noqa: F821

logger = logging.getLogger(__name__)


def start_sync(api_client, repo):
    logger.debug(f"Syncing {repo} repo")
    url = f'content/{repo}/v3/sync/'
    resp = api_client.post(url, b"{}")
    resp = gk_wait_for_task(api_client, resp=None, task_id=resp["task"], raise_on_error=True)
    logger.debug(f"Response from wait_for_task_id {resp}!")


@pytest.mark.sync
@pytest.mark.skipif(not is_sync_testing(),
                    reason="This test can only be run on sync-tests mode")
def test_sync():
    config_sync = get_ansible_config()
    galaxy_client = get_galaxy_client(config_sync)
    gc_remote = galaxy_client("remote_admin", remote=True)
    user_stage = gc_remote.username
    pass_stage = gc_remote.password
    # upload artifact to stage
    test_version = generate_random_artifact_version()
    namespace_name = f"namespace_{uuid4()}"
    namespace_name = namespace_name.replace("-", "")
    gc_remote.create_namespace(namespace_name, "system:partner-engineers")

    artifact = build_collection(
        "skeleton",
        config={"namespace": namespace_name, "version": test_version},
    )
    logger.debug(f"Uploading artifact name {artifact.name} version {artifact.version}")
    resp = upload_artifact(None, gc_remote, artifact)
    api_client_remote = get_client(
        {"url": "https://console.stage.redhat.com/api/automation-hub/",
         "username": user_stage, "password": pass_stage,
         "use_move_endpoint": True, "upload_signatures": True},
        request_token=True, require_auth=True)

    resp = wait_for_task(api_client_remote, resp=resp, raise_on_error=True)
    assert resp["state"] == "completed"

    set_certification(api_client_remote, gc_remote, artifact)

    # sync and check
    body = {
        "url": "https://console.stage.redhat.com/api/"
               "automation-hub/content/1237261-synclist/",
        "username": user_stage,
        "password": pass_stage,
        "tls_validation": False,
        "signed_only": False,
        "proxy_url": "http://squid.corp.redhat.com:3128",
        "requirements_file":
            f"---\ncollections:\n- {artifact.namespace}.{artifact.name}"
    }

    hub_version = get_hub_version(config_sync)
    if parse_version(hub_version) < parse_version('4.5'):
        del body["signed_only"]

    url = "content/community/v3/sync/config/"
    if has_old_credentials():
        gc_local = GalaxyClient(galaxy_root="http://localhost:5001/api/automation-hub/",
                                auth={"username": "admin", "password": "admin"})
    else:
        gc_local = galaxy_client("local_admin")

    gc_local.put(url, body)
    start_sync(gc_local, 'community')

    local_collections = get_all_collections(gc_local, 'community')
    assert retrieve_collection(artifact, local_collections)

    delete_collection(gc_remote, artifact.namespace, artifact.name)
