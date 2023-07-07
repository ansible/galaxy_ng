import logging

import pytest

from galaxykit.namespaces import create_namespace
from galaxykit.remotes import create_remote
from galaxykit.utils import wait_for_task
from ..utils.repo_management_utils import (
    create_repo_and_dist,
    search_collection_endpoint,
    create_test_namespace,
    upload_new_artifact,
    add_content_units,
    verify_repo_data,
)
from ..utils.iqe_utils import GalaxyKitClient
from ..utils.tools import generate_random_string

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.7dev")
class TestCustomReposSync:
    @pytest.mark.sync
    def test_basic_sync_custom_repo_with_req_file(self, sync_instance_crc, galaxy_client):
        """
        Test syncing directly from a custom repo.
        Only the collection specified in the requirements file is fetched
        """
        # this is the insights mode instance (source hub)
        _, custom_config = sync_instance_crc
        url = custom_config["url"]
        galaxy_kit_client = GalaxyKitClient(custom_config)
        source_client = galaxy_kit_client.gen_authorized_client(
            {"username": "notifications_admin", "password": "redhat"}, basic_token=True
        )

        # create repo, distribution, namespace and add a collection
        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        pulp_href = create_repo_and_dist(source_client, test_repo_name_1)
        namespace_name = create_test_namespace(source_client)
        namespace_name_no_sync = create_test_namespace(source_client)
        tags = ["application"]
        artifact = upload_new_artifact(
            source_client, namespace_name, test_repo_name_1, "1.0.1", tags=tags
        )
        collection_resp = source_client.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(source_client, content_units, pulp_href)

        # this artifact is not going to be synced
        artifact_no_sync = upload_new_artifact(
            source_client, namespace_name_no_sync, test_repo_name_1, "1.0.1", tags=tags
        )
        collection_resp_no_sync = source_client.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_no_sync.name}"
        )
        content_units_no_sync = [collection_resp_no_sync["results"][0]["pulp_href"]]
        add_content_units(source_client, content_units_no_sync, pulp_href)

        # this is the standalone mode instance (destination local hub)
        # create repository, distribution and remote in the local hub
        gc = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        params = {
            "auth_url": custom_config["auth_url"],
            "token": custom_config["token"],
            "requirements_file": f"---\ncollections:\n- {artifact.namespace}.{artifact.name}",
        }
        create_remote(
            gc, test_remote_name, f"{url}content/{test_repo_name_1}/", params=params
        )
        create_repo_and_dist(gc, test_repo_name_1, remote=test_remote_name)

        # start sync
        sync_url = f"content/{test_repo_name_1}/v3/sync/"
        r = gc.post(sync_url, body="")
        wait_for_task(gc, r, task_id=r["task"])

        # verify only the collection in the requirement file is synced
        matches, results = search_collection_endpoint(gc, name=artifact.name, limit=100)
        expected = [
            {
                "repo_name": test_repo_name_1,
                "cv_version": "1.0.1",
                "is_highest": True,
                "cv_name": artifact.name,
            }
        ]
        assert verify_repo_data(expected, results)

        matches, _ = search_collection_endpoint(gc, name=artifact_no_sync.name, limit=100)
        assert matches == 0

    @pytest.mark.sync
    def test_basic_sync_custom_repo_mirror(self, sync_instance_crc, galaxy_client):
        """
        Test syncing directly from a custom repo, without a requirements file and checking
        that if the content is not present in the remote repository,
        it's removed from the local repo
        """
        _, custom_config = sync_instance_crc
        url = custom_config["url"]
        galaxy_kit_client = GalaxyKitClient(custom_config)
        source_client = galaxy_kit_client.gen_authorized_client(
            {"username": "notifications_admin", "password": "redhat"}, basic_token=True
        )
        # create repo, distribution, namespace and add a collection
        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        pulp_href = create_repo_and_dist(source_client, test_repo_name_1)
        namespace_name = create_test_namespace(source_client)
        tags = ["application"]
        artifact = upload_new_artifact(
            source_client, namespace_name, test_repo_name_1, "1.0.1", tags=tags
        )
        collection_resp = source_client.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(source_client, content_units, pulp_href)

        # this is the standalone mode instance (destination local hub)
        # create repository, distribution, namespace and remote in the local hub
        gc = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        params = {
            "auth_url": custom_config["auth_url"],
            "token": custom_config["token"],
        }
        create_remote(
            gc, test_remote_name, f"{url}content/{test_repo_name_1}/", params=params
        )
        pulp_href = create_repo_and_dist(gc, test_repo_name_1, remote=test_remote_name)

        create_namespace(gc, namespace_name, "ns_group_for_tests")
        # this artifact is not in the remote repository,
        # so it should be gone after syncing (mirror)
        artifact_will_be_gone = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", tags=tags
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_will_be_gone.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, pulp_href)

        matches, _ = search_collection_endpoint(
            gc, name=artifact_will_be_gone.name, limit=100
        )
        assert matches == 2  # +1 because it's in staging repo

        # start sync
        sync_url = f"content/{test_repo_name_1}/v3/sync/"
        r = gc.post(sync_url, body="")
        wait_for_task(gc, r, task_id=r["task"])

        # artifact has been synced
        _, results = search_collection_endpoint(gc, name=artifact.name, limit=100)
        expected = [
            {
                "repo_name": test_repo_name_1,
                "cv_version": "1.0.1",
                "is_highest": True,
                "cv_name": artifact.name,
            }
        ]
        assert verify_repo_data(expected, results)

        # this artifact has been removed from the repo, now it's only in staging repo
        matches, results = search_collection_endpoint(
            gc, name=artifact_will_be_gone.name, limit=100
        )
        expected = [{"repo_name": "staging", "cv_name": artifact_will_be_gone.name}]
        assert matches == 1
        assert verify_repo_data(expected, results)
