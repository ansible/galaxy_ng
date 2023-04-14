import logging
import os

import pytest

from galaxykit.remotes import create_remote
from galaxykit.repositories import create_repository
from galaxykit.utils import wait_for_task
from .test_x_repo_search import create_test_namespace, upload_new_artifact, search_collection_endpoint, \
    add_content_units, create_repo_and_dist, verify_repo_data
from .test_sync_stage import start_sync
from ..conftest import AnsibleConfigFixture, get_galaxy_client, get_ansible_config
from ..utils import get_client, clear_certified, perform_sync, iterate_all, set_synclist
from ..utils.iqe_utils import GalaxyKitClient
from ..utils.tools import generate_random_string

logger = logging.getLogger(__name__)


@pytest.mark.standalone_only
@pytest.mark.rm_sync
def test_basic_sync_custom_repo(galaxy_client):
    """Test syncing directly from a custom repo."""
    # this is the insights mode instance (source hub)
    url = os.getenv("TEST_CRC_API_ROOT", "http://localhost:8080/api/automation-hub/")
    test_repo_name_1 = f"repo-test-{generate_random_string()}"

    custom_config = {"url": url}
    galaxy_kit_client = GalaxyKitClient(custom_config)
    source_client = galaxy_kit_client.gen_authorized_client({"username": "notifications_admin", "password":"redhat"}, basic_token=True)
    pulp_href = create_repo_and_dist(source_client, test_repo_name_1)

    namespace_name = create_test_namespace(source_client)
    namespace_name_no_sync = create_test_namespace(source_client)
    tags = ["application"]
    artifact = upload_new_artifact(source_client, namespace_name, test_repo_name_1, "1.0.1", tags=tags)
    artifact_no_sync = upload_new_artifact(source_client, namespace_name_no_sync, test_repo_name_1, "1.0.1", tags=tags)

    collection_resp = source_client.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
    content_units = [collection_resp["results"][0]["pulp_href"]]
    add_content_units(source_client, content_units, pulp_href)

    collection_resp_no_sync = source_client.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_no_sync.name}")
    content_units_no_sync = [collection_resp_no_sync["results"][0]["pulp_href"]]
    add_content_units(source_client, content_units_no_sync, pulp_href)

    matches, results = search_collection_endpoint(source_client, name=artifact.name)
    logger.debug(f"Results {results}!")

    # this is the standalone mode instance (destination local hub)
    gc = galaxy_client("iqe_admin")
    test_remote_name = f"remote-test-{generate_random_string()}"
    params = {"auth_url": "http://localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token",
              "token": "abcdefghijklmnopqrstuvwxyz1234567893",
              "requirements_file":
                  f"---\ncollections:\n- {artifact.namespace}.{artifact.name}"
              }
    respuesta = create_remote(gc, test_remote_name, f"{url}content/{test_repo_name_1}/", params=params)
    remote_pulp_href = respuesta["pulp_href"]
    ansible_distribution_path = "/api/automation-hub/pulp/api/v3/distributions/ansible/ansible/"
    repo_res = create_repository(gc, test_repo_name_1, remote=remote_pulp_href)
    dist_data = {"base_path": test_repo_name_1, "name": test_repo_name_1, "repository": repo_res['pulp_href']}
    task_resp = gc.post(ansible_distribution_path, dist_data)
    wait_for_task(gc, task_resp)

    sync_url = f"content/{test_repo_name_1}/v3/sync/"
    r = gc.post(sync_url, body="")
    wait_for_task(gc, r, task_id=r["task"])

    matches, results = search_collection_endpoint(gc, name=artifact.name, limit=100)
    logger.debug(f"Results {results}!")
    expected = [{"repo_name": test_repo_name_1, "cv_version": "1.0.1", "is_highest": True, "cv_name": artifact.name}]
    assert verify_repo_data(expected, results)

    matches, _ = search_collection_endpoint(gc, name=artifact_no_sync.name, limit=100)
    assert matches == 0


