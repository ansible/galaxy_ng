import pytest
import logging

from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.rbac_utils import upload_test_artifact
from orionutils.generator import build_collection

from galaxy_ng.tests.integration.utils.tools import generate_random_artifact_version
from galaxykit.collections import delete_collection, deprecate_collection, collection_sign, sign_collection
from galaxykit.namespaces import create_namespace
from galaxykit.repositories import get_all_repositories, delete_repository, create_repository, search_collection, \
    set_certification, get_distribution_id
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
    return repo_res['pulp_href']


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


def search_collection_endpoint(client, **params):
    result = search_collection(client, **params)
    new_results = edit_results_for_verification(result)
    return result["meta"]["count"], new_results


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
            logger.debug(f"{expected_repo} not found in actual repos")
            return False
    return True


@pytest.mark.min_hub_version("4.6dev")  # set correct min hub version
class TestRM:
    @pytest.mark.rm
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

    @pytest.mark.rm
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


    @pytest.mark.rm
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
        matches, result = search_collection_endpoint(gc, name=artifact.name)
        expected = [{"repo_name": test_repo_name, "cv_name": artifact.name}]
        assert verify_repo_data(expected, result)
        assert matches == 2  # +1 (staging)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_same_repo_diff_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")

        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

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
        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        matches, result = search_collection_endpoint(gc, repository_name=test_repo_name, name=artifact_1.name)

        assert matches == 2
        expected = [{"repo_name": test_repo_name, "cv_version": "0.0.2", "is_highest": True},
                    {"is_highest": False, "cv_version": "0.0.1"}]
        assert verify_repo_data(expected, result)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_diff_repo_diff_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

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

        resp_task = gc.post(f"{repo_pulp_href_1}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_2}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        _, results = search_collection_endpoint(gc, name=artifact_1.name)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_diff_repo_same_versions(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

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

        resp_task = gc.post(f"{repo_pulp_href_1}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_2}modify/", body=payload_1)
        wait_for_task(gc, resp_task)

        _, results = search_collection_endpoint(gc, name=artifact_1.name)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
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

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_diff_collection_diff_namespaces(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

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
        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        _, results = search_collection_endpoint(gc, repository_name=test_repo_name)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_diff_repo_diff_versions_check_both_is_highest(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-test-{uuid4()}"
        test_repo_name_2 = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

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

        resp_task = gc.post(f"{repo_pulp_href_1}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_2}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        _, results = search_collection_endpoint(gc, name=artifact_1.name)

        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True},
                    {"repo_name": test_repo_name_2, "cv_name": artifact_1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_upload_same_collection_same_repo_diff_versions_delete_check_is_highest(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

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

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        _, results = search_collection_endpoint(gc, name=artifact_1.name)
        expected = [{"cv_version": "0.0.2", "is_highest": True}, {"cv_version": "0.0.1", "is_highest": False}]
        assert verify_repo_data(expected, results)
        delete_collection(gc, namespace_name, artifact_1.name, version="0.0.2", repository=test_repo_name)
        _, results = search_collection_endpoint(gc, name=artifact_1.name)
        expected = [{"cv_version": "0.0.1", "is_highest": True}]
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_delete_repo_with_contents(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

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

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        delete_repository(gc, test_repo_name)
        repos = get_all_repositories(gc)
        assert not repo_exists(test_repo_name, repos)
        _, results = search_collection_endpoint(gc, name=artifact.name)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_deprecate_collection(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

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

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        deprecate_collection(gc, namespace_name, artifact.name, repository=test_repo_name)

        _, results = search_collection_endpoint(gc, repository_name=test_repo_name, name=artifact.name)
        expected = [{"repo_name": test_repo_name, "is_deprecated": True}]
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_cv_that_does_not_exist(self, galaxy_client):
        """
        Verifies
        """
        gc = galaxy_client("iqe_admin")
        matches, _ = search_collection_endpoint(gc, name=f"does-not-exist-{uuid4()}")
        assert matches == 0

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_cv_that_does_not_exit(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-1-{uuid4()}"
        test_repo_name_2 = f"repo-2-{uuid4()}"
        test_repo_name_3 = f"repo-3-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)
        repo_pulp_href_3 = create_repo_and_dist(gc, test_repo_name_3)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        key_1 = f"test_{uuid4()}"
        key_1 = key_1.replace("-", "")

        key_2 = f"test_{uuid4()}"
        key_2 = key_2.replace("-", "")

        key_3 = f"test_{uuid4()}"
        key_3 = key_3.replace("-", "")

        artifact_1v1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
            key=key_1
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1v1)

        artifact_2v2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name_1},
            key=key_2
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_2v2)

        artifact_2v1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_2},
            key=key_2
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_2, artifact_2v1)

        artifact_3v1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_2},
            key=key_3
        )

        upload_test_artifact(gc, namespace_name, test_repo_name_2, artifact_3v1)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1v1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2v1.name}")
        collection_resp_3 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_3v1.name}")

        payload_1 = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"], collection_resp_2["results"][1]["pulp_href"]]}
        payload_2 = {"add_content_units": [collection_resp_2["results"][0]["pulp_href"], collection_resp_3["results"][0]["pulp_href"]]}
        payload_3 = {"add_content_units": [collection_resp_3["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href_1}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_2}modify/", body=payload_2)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_3}modify/", body=payload_3)
        wait_for_task(gc, resp_task)

        _, results = search_collection_endpoint(gc, name=artifact_1v1.name)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1v1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)

        _, results = search_collection_endpoint(gc, name=artifact_2v1.name)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_2v1.name, "cv_version": "0.0.2", "is_highest": True},
                    {"repo_name": test_repo_name_2, "cv_name": artifact_2v1.name, "cv_version": "0.0.1", "is_highest": True}]
        assert verify_repo_data(expected, results)

        _, results = search_collection_endpoint(gc, name=artifact_3v1.name)
        expected = [{"repo_name": test_repo_name_2, "cv_name": artifact_3v1.name, "cv_version": "0.0.1", "is_highest": True},
                    {"repo_name": test_repo_name_3, "cv_name": artifact_3v1.name, "cv_version": "0.0.1", "is_highest": True}]
        assert verify_repo_data(expected, results)

        matches, _ = search_collection_endpoint(gc, repository_name=f"does-not-exist-{uuid4()}")
        assert matches == 0

        matches, _ = search_collection_endpoint(gc, repository_name=f"does-not-exist-{uuid4()}", name=artifact_1v1.name)
        assert matches == 0

        matches, _ = search_collection_endpoint(gc, repository_name=test_repo_name_2, name=artifact_1v1.name)
        assert matches == 0

        matches, _ = search_collection_endpoint(gc, repository_name=test_repo_name_1, name=artifact_1v1.name)
        assert matches == 1

        matches, _ = search_collection_endpoint(gc, name=artifact_3v1.name)
        assert matches == 3  # +1 because it's staging

        delete_collection(gc, namespace_name, artifact_3v1.name, version="0.0.1", repository=test_repo_name_3)
        matches, results = search_collection_endpoint(gc, name=artifact_3v1.name)
        expected = [{"repo_name": test_repo_name_2, "cv_name": artifact_3v1.name}]
        assert matches == 2  # +1 because it's staging
        # this fails, because the collection is gone from all repos. Is it correct?
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_or(self, galaxy_client):
        """
        Verifies THIS CAN BE DELETED IN FAVOR OF or_2
        """
        test_repo_name_1 = f"repo-1-{uuid4()}"
        test_repo_name_2 = f"repo-2-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")

        payload_1 = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}
        payload_2 = {"add_content_units": [collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href_1}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_2}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        matches, results = search_collection_endpoint(gc, repository_name=test_repo_name_1)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

        matches, results = search_collection_endpoint(gc, repository_name=[test_repo_name_1, test_repo_name_2])
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True},
                    {"repo_name": test_repo_name_2, "cv_name": artifact_2.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 2

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_or_2(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-1-{uuid4()}"
        test_repo_name_2 = f"repo-2-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.2", "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")

        payload_1 = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}
        payload_2 = {"add_content_units": [collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href_1}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        resp_task = gc.post(f"{repo_pulp_href_2}modify/", body=payload_2)
        wait_for_task(gc, resp_task)

        matches, results = search_collection_endpoint(gc, repository_name=test_repo_name_1)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

        matches, results = search_collection_endpoint(gc, repository_name=[test_repo_name_1, test_repo_name_2, f"does-not-exist-{uuid4()}"])
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True},
                    {"repo_name": test_repo_name_2, "cv_name": artifact_2.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 2

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_repo_id(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-1-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name_1)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        repository_id = repo_pulp_href.split("/")[-2]
        matches, results = search_collection_endpoint(gc, repository=repository_id)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_namesapce(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-1-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name_1)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        matches, results = search_collection_endpoint(gc, namespace=namespace_name)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 2  # staging

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_version(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name_1 = f"repo-1-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name_1)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        version = generate_random_artifact_version()
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": version, "repository_name": test_repo_name_1},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name_1, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")

        payload_1 = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload_1)
        wait_for_task(gc, resp_task)
        matches, results = search_collection_endpoint(gc, version=version)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "cv_version": version}]
        assert verify_repo_data(expected, results)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_is_highest_true(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-1-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.1", "repository_name": test_repo_name}, key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}, key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"],
                                         collection_resp["results"][1]["pulp_href"]]}
        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        matches, results = search_collection_endpoint(gc, repository_name=test_repo_name, is_highest=True)
        expected = [{"repo_name": test_repo_name, "cv_name": artifact_2.name, "cv_version": "4.0.2"}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_is_highest_false(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-1-{uuid4()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        key = f"test_{uuid4()}"
        key = key.replace("-", "")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.1", "repository_name": test_repo_name}, key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}, key=key
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp["results"][0]["pulp_href"],
                                         collection_resp["results"][1]["pulp_href"]]}
        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        matches, results = search_collection_endpoint(gc, repository_name=test_repo_name, is_highest=False)
        expected = [{"repo_name": test_repo_name, "cv_name": artifact_2.name, "cv_version": "4.0.1"}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_by_is_deprecated_true(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        deprecate_collection(gc, namespace_name, artifact_1.name, repository=test_repo_name)

        matches, results = search_collection_endpoint(gc, is_deprecated=True, repository_name=test_repo_name)
        expected = [{"cv_name": artifact_1.name, "is_deprecated": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_by_is_deprecated_false(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        deprecate_collection(gc, namespace_name, artifact_1.name, repository=test_repo_name)

        matches, results = search_collection_endpoint(gc, is_deprecated=False, repository_name=test_repo_name)
        expected = [{"cv_name": artifact_2.name, "is_deprecated": False}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_by_q(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        tag = f"tag{uuid4()}"
        tag = tag.replace("-", "")
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name, "tags": [tag]},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        matches, results = search_collection_endpoint(gc, q=tag)
        expected = [{"cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)
        assert matches == 2  # staging

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_by_tags_ok(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        tag = f"tag{uuid4()}"
        tag = tag.replace("-", "")
        tags = ["test_tag_1", "test_tag_2", tag]
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name, "tags": tags},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        matches, results = search_collection_endpoint(gc, tags="test_tag_1,test_tag_2", repository_name=test_repo_name)
        expected = [{"cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)
        assert matches == 1
        matches, results = search_collection_endpoint(gc, tags="test_tag_1,test_tag_3", repository_name=test_repo_name)
        assert matches == 0

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_by_signed(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        tag = f"tag{uuid4()}"
        tag = tag.replace("-", "")
        tags = ["test_tag_1", "test_tag_2", tag]
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name, "tags": tags},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)

        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "4.0.2", "repository_name": test_repo_name}
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)

        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)

        # how to sign
        sign_collection(gc, collection_resp_1["results"][0]["pulp_href"], repo_pulp_href)

        matches, results = search_collection_endpoint(gc, is_signed=True, repository_name=test_repo_name)
        expected = [{"cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)
        assert matches == 1
        matches, results = search_collection_endpoint(gc, is_signed=False, repository_name=test_repo_name)
        expected = [{"cv_name": artifact_2.name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_distribution_id(self, galaxy_client):
        """
        Verifies
        ?distribution=46651634-bdca-44f8-88da-d854237ea51
         raise ValueError('badly formed hexadecimal UUID string')

        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        distribution_id = get_distribution_id(gc, test_repo_name)
        matches, results = search_collection_endpoint(gc, distribution=distribution_id)
        expected = [{"cv_name": artifact_1.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_base_path(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        matches, results = search_collection_endpoint(gc, distribution_base_path=test_repo_name)
        expected = [{"cv_name": artifact_1.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_dependency(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        dep = f"dep{uuid4()}"
        dep = dep.replace("-", "")
        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name,
                    "dependencies": {f"names.{dep}": "1.0.0"}},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        matches, results = search_collection_endpoint(gc, dependency=f"names.{dep}")
        expected = [{"cv_name": artifact_1.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 2  # staging (+1)

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_repo_version(self, galaxy_client):
        """
        Verifies HOW DOES IT WORK
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "0.0.1", "repository_name": test_repo_name,
                    "dependencies": {"names.python": "1.0.0"}},
        )

        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        matches, results = search_collection_endpoint(gc, repository_version="names.python")
        expected = [{"cv_name": artifact_1.name, "repository_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.rm
    @pytest.mark.standalone_only
    def test_search_version_range(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{uuid4()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)

        namespace_name = f"namespace_{uuid4()}"
        namespace_name = namespace_name.replace("-", "")
        create_namespace(gc, namespace_name, "ns_group_for_tests")

        artifact_1 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "6.6.6", "repository_name": test_repo_name},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_1)
        collection_resp_1 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}")
        artifact_2 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "8.8.8", "repository_name": test_repo_name},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_2)
        collection_resp_2 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}")
        artifact_3 = build_collection(
            "skeleton",
            config={"namespace": namespace_name, "version": "12.6.6", "repository_name": test_repo_name},
        )
        upload_test_artifact(gc, namespace_name, test_repo_name, artifact_3)
        collection_resp_3 = gc.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_3.name}")
        payload = {"add_content_units": [collection_resp_1["results"][0]["pulp_href"],
                                         collection_resp_2["results"][0]["pulp_href"],
                                         collection_resp_3["results"][0]["pulp_href"]]}

        resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
        wait_for_task(gc, resp_task)
        matches, results = search_collection_endpoint(gc, version_range='>=6.6.6,<8.8.8', repository_name=test_repo_name)
        expected = [{"cv_name": artifact_1.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

        matches, results = search_collection_endpoint(gc, version_range='>=6.6.6', repository_name=test_repo_name)
        expected = [{"cv_name": artifact_2.name, "repo_name": test_repo_name}, {"cv_name": artifact_1.name, "repo_name": test_repo_name}, {"cv_name": artifact_3.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 3

        matches, results = search_collection_endpoint(gc, version_range='<=8.8.8', repository_name=test_repo_name)
        expected = [{"cv_name": artifact_2.name, "repo_name": test_repo_name}, {"cv_name": artifact_1.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 2



    # hide from searching field ?
    # pipeline: approved no one can upload
    # pipeline: staging, those with rbac permissions can upload
    # both are hidden from search


