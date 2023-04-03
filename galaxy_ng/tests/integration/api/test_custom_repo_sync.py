import os

import pytest

from galaxykit.remotes import create_remote
from galaxykit.repositories import create_repository
from galaxykit.utils import wait_for_task
from ..conftest import AnsibleConfigFixture, get_galaxy_client, get_ansible_config
from ..utils import get_client, clear_certified, perform_sync, iterate_all, set_synclist
from ..utils.iqe_utils import GalaxyKitClient
from ..utils.tools import generate_random_string


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
    r = create_repository(source_client, test_repo_name_1)

    # this is the standalone mode instance (destination local hub)
    gc = galaxy_client("iqe_admin")
    test_remote_name = f"remote-test-{generate_random_string()}"
    params = {"auth_url": "http://localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token",
              "token": "abcdefghijklmnopqrstuvwxyz1234567893"
              }
    respuesta = create_remote(gc, test_remote_name, url, params=params)
    remote_pulp_href = respuesta["pulp_href"]
    ansible_distribution_path = "/api/automation-hub/pulp/api/v3/distributions/ansible/ansible/"
    repo_res = create_repository(gc, test_repo_name_1, remote=remote_pulp_href)
    dist_data = {"base_path": test_repo_name_1, "name": test_repo_name_1, "repository": repo_res['pulp_href']}
    task_resp = gc.post(ansible_distribution_path, dist_data)
    wait_for_task(gc, task_resp)


