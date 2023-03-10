"""
(iqe) tests for rbac
Imported from https://gitlab.cee.redhat.com/insights-qe/iqe-automation-hub-plugin/
"""
import pytest
import logging

from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group, \
    create_test_user, upload_test_artifact
from orionutils.generator import build_collection
from galaxykit.namespaces import create_namespace
from galaxykit.repositories import get_all_repositories, delete_repository, create_repository, search_collection, \
    set_certification
from galaxykit.utils import wait_for_task

logger = logging.getLogger(__name__)


def repo_exists(name, repo_list):
    for repo in repo_list:
        if repo["name"] == name:
            return True
    return False


def create_repo_and_dist(client, repo_name):
    ansible_distribution_path = "/api/automation-hub/pulp/api/v3/distributions/ansible/ansible/"
    logger.debug(f"creating repo {repo_name}")
    repo_res = create_repository(client, repo_name)
    dist_data = {"base_path": repo_name, "name": repo_name, "repository": repo_res['pulp_href']}
    logger.debug(f"creating dist with this data {dist_data}")
    task_resp = client.post(ansible_distribution_path, dist_data)
    wait_for_task(client, task_resp)
    return dist_data


@pytest.mark.min_hub_version("4.6dev")  # set correct min hub version
class TestRM:

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_create_repository(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        create_repository(gc, test_repo_name)
        repos = get_all_repositories(gc)
        assert repo_exists(test_repo_name, repos)

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_delete_repository(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        create_repository(gc, test_repo_name)
        repos = get_all_repositories(gc)
        assert repo_exists(test_repo_name, repos)
        delete_repository(gc, test_repo_name)
        repos = get_all_repositories(gc)
        assert not repo_exists(test_repo_name, repos)

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_upload_content_to_new_repository(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        create_repository(gc, test_repo_name)
        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        upload_test_artifact(gc, namespace_name)
        # the moving does not work yet
        # POST http://localhost:5001/api/automation-hub/v3/collections/namespace_1ca591cc66f04b9daee8a9ebeabd83c9/collection_dep_a_ejrhoshf/versions/42.100.59/move/published/christian-repo/
        # "detail": "Repo(s) for moving collection namespace_1ca591cc66f04b9daee8a9ebeabd83c9-collection_dep_a_ejrhoshf-42.100.59 not found"

    # http://localhost:5001/pulp_ansible/galaxy/default/api/v3/plugin/ansible/search/collection-versions/?repository=published&name=collection_dep_a_ejrhoshf

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_res = create_repository(gc, test_repo_name)
        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        artifact = upload_test_artifact(gc, namespace_name, test_repo_name)
        set_certification(gc, artifact)
        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}
        resp_task = gc.post(f"{repo_res['pulp_href']}modify/", body=payload)
        wait_for_task(gc, resp_task)
        result = search_collection(gc, search_string=artifact.name)
        logger.debug(result)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_colection_same_repo_diff_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")

        dist_data = create_repo_and_dist(gc, test_repo_name)
        logger.debug(dist_data)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name}, key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name}, key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"],
                                         collection_resp["results"][1]["pulp_href"]]}
        resp_task = gc.post(f"{dist_data['repository']}modify/", body=payload)
        wait_for_task(gc, resp_task)
        result = search_collection(gc, repository=test_repo_name, search_string=artifact_1.name)
        logger.debug(result)
        assert result["meta"]["count"] == 2
        assert result["data"][1]["is_highest"] is False
        assert result["data"][0]["is_highest"] is True
        assert result["data"][0]["collection_version"]["version"] == "0.0.2"
        assert result["data"][0]["repository"]["name"] == test_repo_name

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_colection_diff_repo_diff_versions(self, galaxy_client):
        """
        Verifies TODO
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_res = create_repository(gc, test_repo_name_1)
        repo_res = create_repository(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
            key="test_rm_1"
        )

        artifact_1 = upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)
        set_certification(gc, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name_2},
            key="test_rm_1"
        )

        artifact_2 = upload_test_artifact(gc, namespace_name, test_repo_name_2, artifact_2)
        set_certification(gc, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}
        resp_task = gc.post(f"{repo_res['pulp_href']}modify/", body=payload)
        wait_for_task(gc, resp_task)
        result = search_collection(gc, search_string=artifact_1.name)
        logger.debug(result)

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_colection_diff_repo_same_versions(self, galaxy_client):
        """
        Verifies TODO
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_res = create_repository(gc, test_repo_name_1)
        repo_res = create_repository(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
            key="test_rm_2"
        )

        artifact_1 = upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)
        set_certification(gc, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_2},
            key="test_rm_2"
        )

        artifact_2 = upload_test_artifact(gc, namespace_name, test_repo_name_2, artifact_2)
        set_certification(gc, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}
        resp_task = gc.post(f"{repo_res['pulp_href']}modify/", body=payload)
        wait_for_task(gc, resp_task)
        result = search_collection(gc, search_string=artifact_1.name)
        logger.debug(result)

# upload same collection same version same repo
# upload diff collection same repo
