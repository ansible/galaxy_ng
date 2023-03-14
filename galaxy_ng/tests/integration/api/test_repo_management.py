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

from galaxykit.collections import delete_collection, deprecate_collection
from galaxykit.namespaces import create_namespace
from galaxykit.repositories import get_all_repositories, delete_repository, create_repository, search_collection, \
    set_certification
from galaxykit.utils import wait_for_task, GalaxyClientError

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
    logger.debug(f"Repository creation response {repo_res}")
    dist_data = {"base_path": repo_name, "name": repo_name, "repository": repo_res['pulp_href']}
    logger.debug(f"creating dist with this data {dist_data}")
    task_resp = client.post(ansible_distribution_path, dist_data)
    wait_for_task(client, task_resp)
    return dist_data


def edit_results_for_verification(results):
    _results = results["data"]
    new_results = []
    for data in _results:
        repo_name = data["repository"]["name"]
        cv_name = data["collection_version"]["name"]
        cv_version = data["collection_version"]["version"]
        is_highest = data["is_highest"]
        is_deprecated = data["is_deprecated"]
        is_signed = data["is_signed"]
        new_result = {"repo_name": repo_name, "cv_name": cv_name, "cv_version": cv_version, "is_highest": is_highest,
                      "is_deprecated": is_deprecated, "is_signed": is_signed}
        new_results.append(new_result)
    return new_results

def verify_repo_data(expected_repos, actual_repos):
    def is_dict_included(dict1, dict2):
        # Check if all key-value pairs in dict1 are present in dict2
        for key, value in dict1.items():
            if key not in dict2 or dict2[key] != value:
                return False
        return True
    for expected_repo in expected_repos:
        found = False
        for actual_repo in actual_repos:
            if is_dict_included(expected_repo, actual_repo):
                found = True
        if not found:
            return False
    return True


@pytest.mark.min_hub_version("4.6dev")  # set correct min hub version
class TestRM:
    #@pytest.mark.rm
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

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_same_repo_diff_versions(self, galaxy_client):
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
    def test_search_upload_same_collection_diff_repo_diff_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        dist_data_1 = create_repo_and_dist(gc, test_repo_name_1)
        dist_data_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name_2},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_2, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}
        payload_2 = {"add_content_units": [collection_resp["results"][1]["pulp_href"]]}

        resp_task = gc.post(f"{dist_data_1['repository']}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{dist_data_2['repository']}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        results = search_collection(gc, search_string=artifact_1.name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        logger.debug(new_results)
        for data in new_results:
            if data["repo_name"] == test_repo_name_1:
                assert data["cv_name"] == artifact_1.name

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_diff_repo_same_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        dist_data_1 = create_repo_and_dist(gc, test_repo_name_1)
        dist_data_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{dist_data_1['repository']}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{dist_data_2['repository']}modify/", body=payload_1)
        wait_for_task(gc, resp_task)

        results = search_collection(gc, search_string=artifact_1.name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        logger.debug(new_results)
        for data in new_results:
            if data["repo_name"] == test_repo_name_1:
                assert data["cv_name"] == artifact_1.name

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_same_repo_same_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        create_repo_and_dist(gc, test_repo_name)
        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact)

        with pytest.raises(GalaxyClientError) as ctx:
            upload_test_artifact(gc, namespace_name, test_repo_name, artifact)
        assert ctx.value.response.status_code == 400

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_diff_collection_diff_namespaces(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        dist_data = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        namespace_name_mod = namespace_name + "_mod"
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        create_namespace(gc, namespace_name + "_mod", "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name_mod, "version": "0.0.2", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name_mod, test_repo_name, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")

        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"]]}
        resp_task = gc.post(f"{dist_data['repository']}modify/", body=payload)
        wait_for_task(gc, resp_task)

        results = search_collection(gc, repository=test_repo_name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        logger.debug(new_results)

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_diff_repo_diff_versions_check_both_is_highest(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        dist_data_1 = create_repo_and_dist(gc, test_repo_name_1)
        dist_data_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name_2},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_2, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}
        payload_2 = {"add_content_units": [collection_resp["results"][1]["pulp_href"]]}

        resp_task = gc.post(f"{dist_data_1['repository']}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{dist_data_2['repository']}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        results = search_collection(gc, search_string=artifact_1.name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        logger.debug(new_results)

        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True},
                    {"repo_name": test_repo_name_2, "cv_name": artifact_1.name, "is_highest": True}]
        verify_repo_data(expected, new_results)
        '''
        for data in new_results:
            if data["repo_name"] == test_repo_name_1:
                assert data["cv_name"] == artifact_1.name
                assert data["is_highest"] is True
            if data["repo_name"] == test_repo_name_2:
                assert data["cv_name"] == artifact_1.name
                assert data["is_highest"] is True
        '''
    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_same_repo_diff_versions_delete_check_is_highest(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        dist_data = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name},
            key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}
        payload_2 = {"add_content_units": [collection_resp["results"][1]["pulp_href"]]}

        resp_task = gc.post(f"{dist_data['repository']}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{dist_data['repository']}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        results = search_collection(gc, search_string=artifact_1.name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        logger.debug(new_results)
        '''
        for data in new_results:
            if data["cv_version"] == "0.0.2":
                assert data["is_highest"] is True
            if data["cv_version"] == "0.0.1":
                assert data["is_highest"] is False
        '''

        expected = [{"cv_version": "0.0.2", "is_highest": True}, {"cv_version": "0.0.1", "is_highest": False}]
        assert verify_repo_data(expected, new_results)
        delete_collection(gc, namespace_name, artifact_1.name, version="0.0.2", repository=test_repo_name)
        results = search_collection(gc, search_string=artifact_1.name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        logger.debug(new_results)
        expected = [{"cv_version": "0.0.1", "is_highest": True}]
        assert verify_repo_data(expected, new_results)

    # @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_delete_repo_with_contents(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        dist_data = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")

        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{dist_data['repository']}modify/", body=payload)
        wait_for_task(gc, resp_task)
        delete_repository(gc, test_repo_name)
        repos = get_all_repositories(gc)
        assert not repo_exists(test_repo_name, repos)
        results = search_collection(gc, search_string=artifact.name)
        logger.debug(results)

    #@pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_deprecate_collection(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        dist_data = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")

        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{dist_data['repository']}modify/", body=payload)
        wait_for_task(gc, resp_task)

        deprecate_collection(gc, namespace_name, artifact.name, repository=test_repo_name)

        results = search_collection(gc, repository=test_repo_name, search_string=artifact.name)
        logger.debug(results)
        new_results = edit_results_for_verification(results)
        expected = {"repo_name": test_repo_name, "is_deprecated": True}
        verify_repo_data(expected, new_results)
