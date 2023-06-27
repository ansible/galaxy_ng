import pytest
import logging

from galaxy_ng.tests.integration.utils.iqe_utils import is_ocp_env
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group

from galaxy_ng.tests.integration.utils.repo_management_utils import (
    repo_exists,
    create_repo_and_dist,
    search_collection_endpoint,
    create_test_namespace,
    upload_new_artifact,
    add_content_units,
    verify_repo_data,
)
from galaxy_ng.tests.integration.utils.tools import (
    generate_random_artifact_version,
    generate_random_string,
)
from galaxykit.collections import delete_collection, deprecate_collection, sign_collection
from galaxykit.namespaces import create_namespace
from galaxykit.repositories import get_all_repositories, delete_repository, get_distribution_id

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.7dev")
class TestXRepoSearch:
    @pytest.mark.x_repo_search
    def test_search_same_collection_diff_versions_same_repo(self, galaxy_client):
        """
        Verifies that one collection with diff versions in the same repo
        is found and the is_highest flag is correct
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")

        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        key = generate_random_string()
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(gc, namespace_name, test_repo_name, "1.0.2", key, tags=["application"])

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [
            collection_resp["results"][0]["pulp_href"],
            collection_resp["results"][1]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, result = search_collection_endpoint(
            gc, repository_name=test_repo_name, name=artifact.name
        )
        assert matches == 2
        expected = [
            {"repo_name": test_repo_name, "cv_version": "1.0.2", "is_highest": True},
            {"is_highest": False, "cv_version": "1.0.1"},
        ]
        assert verify_repo_data(expected, result)

    @pytest.mark.x_repo_search
    def test_search_same_collection_diff_versions_diff_repo(self, galaxy_client):
        """
        Verifies that one collection with diff versions in diff repos is found
        """
        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        test_repo_name_2 = f"repo-test-{generate_random_string()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = create_test_namespace(gc)
        key = generate_random_string()
        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(
            gc, namespace_name, test_repo_name_2, "1.0.2", key, tags=["application"]
        )

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )

        content_units_1 = [collection_resp["results"][1]["pulp_href"]]
        content_units_2 = [collection_resp["results"][0]["pulp_href"]]

        add_content_units(gc, content_units_1, repo_pulp_href_1)
        add_content_units(gc, content_units_2, repo_pulp_href_2)

        _, results = search_collection_endpoint(gc, name=artifact_1.name)
        expected = [
            {"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "cv_version": "1.0.1"},
            {"repo_name": test_repo_name_2, "cv_name": artifact_1.name, "cv_version": "1.0.2"},
        ]
        assert verify_repo_data(expected, results)

    @pytest.mark.x_repo_search
    def test_search_same_collection_diff_repo_same_versions(self, galaxy_client):
        """
        Verifies that one collection with the same version in diff repos is found
        """
        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href_1)
        add_content_units(gc, content_units, repo_pulp_href_2)
        _, results = search_collection_endpoint(gc, name=artifact.name)
        expected = [
            {"repo_name": test_repo_name_1, "cv_name": artifact.name, "cv_version": "1.0.1"},
            {"repo_name": test_repo_name_2, "cv_name": artifact.name, "cv_version": "1.0.1"},
        ]
        assert verify_repo_data(expected, results)

    @pytest.mark.x_repo_search
    def test_search_upload_diff_collection_diff_namespaces(self, galaxy_client):
        """
        Verifies that two collections in different namespaces in the same repo are found
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = f"ns_{generate_random_string()}"
        namespace_name_mod = namespace_name + "_mod"
        create_namespace(gc, namespace_name, "ns_group_for_tests")
        create_namespace(gc, namespace_name + "_mod", "ns_group_for_tests")

        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        artifact_2 = upload_new_artifact(
            gc, namespace_name_mod, test_repo_name, "1.0.2", tags=["application"]
        )

        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        content_units = [
            collection_resp_1["results"][0]["pulp_href"],
            collection_resp_2["results"][0]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)
        _, results = search_collection_endpoint(gc, repository_name=test_repo_name)
        expected = [
            {"repo_name": test_repo_name, "cv_name": artifact_1.name, "cv_version": "1.0.1"},
            {"repo_name": test_repo_name, "cv_name": artifact_2.name, "cv_version": "1.0.2"},
        ]
        assert verify_repo_data(expected, results)

    @pytest.mark.x_repo_search
    def test_search_upload_same_collection_diff_repo_diff_versions_check_both_is_highest(
        self, galaxy_client
    ):
        """
        Verifies that same collection name with two different versions
        in two different repos is_highest is True for both versions
        """
        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)
        namespace_name = create_test_namespace(gc)

        key = generate_random_string()
        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(
            gc, namespace_name, test_repo_name_2, "1.0.2", key, tags=["application"]
        )

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        content_units_1 = [collection_resp["results"][0]["pulp_href"]]
        content_units_2 = [collection_resp["results"][1]["pulp_href"]]
        add_content_units(gc, content_units_1, repo_pulp_href_1)
        add_content_units(gc, content_units_2, repo_pulp_href_2)

        _, results = search_collection_endpoint(gc, name=artifact_1.name)

        expected = [
            {"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True},
            {"repo_name": test_repo_name_2, "cv_name": artifact_1.name, "is_highest": True},
        ]
        assert verify_repo_data(expected, results)

    @pytest.mark.x_repo_search
    def test_search_is_highest_changes_after_deletion(self, galaxy_client):
        """
        Verifies that lower version becomes is_highest True when higher version is deleted
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)

        key = generate_random_string()
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(gc, namespace_name, test_repo_name, "1.0.2", key, tags=["application"])
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )

        content_units_1 = [collection_resp["results"][0]["pulp_href"]]
        content_units_2 = [collection_resp["results"][1]["pulp_href"]]
        add_content_units(gc, content_units_1, repo_pulp_href)
        add_content_units(gc, content_units_2, repo_pulp_href)

        _, results = search_collection_endpoint(gc, name=artifact.name)
        expected = [
            {"cv_version": "1.0.2", "is_highest": True},
            {"cv_version": "1.0.1", "is_highest": False},
        ]
        assert verify_repo_data(expected, results)
        delete_collection(
            gc, namespace_name, artifact.name, version="1.0.2", repository=test_repo_name
        )
        _, results = search_collection_endpoint(gc, name=artifact.name)
        expected = [{"cv_version": "1.0.1", "is_highest": True}]
        assert verify_repo_data(expected, results)

    @pytest.mark.x_repo_search
    def test_search_deprecated_collection(self, galaxy_client):
        """
        Verifies is_deprecated flag
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        deprecate_collection(gc, namespace_name, artifact.name, repository=test_repo_name)
        matches, results = search_collection_endpoint(
            gc, repository_name=test_repo_name, name=artifact.name
        )
        expected = [{"repo_name": test_repo_name, "is_deprecated": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.x_repo_search
    def test_search_cv_that_does_not_exist(self, galaxy_client):
        """
        Verifies that search endpoint returns no results when a non-existing cv is searched
        """
        gc = galaxy_client("iqe_admin")
        matches, _ = search_collection_endpoint(
            gc, name=f"does-not-exist-{generate_random_string()}"
        )
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_search_by_repository_name_or_operator(self, galaxy_client):
        """
        Verifies that search endpoint can take several repository_name params (OR)
        """
        test_repo_name_1 = f"repo-test-1-{generate_random_string()}"
        test_repo_name_2 = f"repo-test-2-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)

        namespace_name = create_test_namespace(gc)
        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        artifact_2 = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.2", tags=["application"]
        )

        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        content_units_1 = [collection_resp_1["results"][0]["pulp_href"]]
        content_units_2 = [collection_resp_2["results"][0]["pulp_href"]]

        add_content_units(gc, content_units_1, repo_pulp_href_1)
        add_content_units(gc, content_units_2, repo_pulp_href_2)

        matches, results = search_collection_endpoint(gc, repository_name=test_repo_name_1)
        expected = [{"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

        matches, results = search_collection_endpoint(
            gc,
            repository_name=[
                test_repo_name_1,
                test_repo_name_2,
                f"does-not-exist-{generate_random_string()}",
            ],
        )
        expected = [
            {"repo_name": test_repo_name_1, "cv_name": artifact_1.name, "is_highest": True},
            {"repo_name": test_repo_name_2, "cv_name": artifact_2.name, "is_highest": True},
        ]
        assert verify_repo_data(expected, results)
        assert matches == 2

    @pytest.mark.x_repo_search
    def test_search_by_repository_id(self, galaxy_client):
        """
        Verifies that search endpoint accepts repository id as search param
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        repository_id = repo_pulp_href.split("/")[-2]
        matches, results = search_collection_endpoint(gc, repository=repository_id)
        expected = [{"repo_name": test_repo_name, "cv_name": artifact.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.x_repo_search
    def test_search_by_namespace(self, galaxy_client):
        """
        Verifies that search endpoint can search by namespace
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, results = search_collection_endpoint(gc, namespace=namespace_name)
        expected = [{"repo_name": test_repo_name, "cv_name": artifact.name, "is_highest": True}]
        assert verify_repo_data(expected, results)
        assert matches == 2  # staging

    @pytest.mark.x_repo_search
    def test_search_by_version(self, galaxy_client):
        """
        Verifies that search endpoint can search by version
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        version = generate_random_artifact_version()
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, version, tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, results = search_collection_endpoint(gc, version=version)
        expected = [{"repo_name": test_repo_name, "cv_name": artifact.name, "cv_version": version}]
        assert verify_repo_data(expected, results)

    @pytest.mark.parametrize("is_highest,cv_version", [(True, "4.0.2"), (False, "4.0.1")])
    @pytest.mark.x_repo_search
    def test_search_is_highest_true_false(self, galaxy_client, is_highest, cv_version):
        """
        Verifies that search endpoint can search by is_highest parameter
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        key = generate_random_string()

        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "4.0.1", key, tags=["application"]
        )
        upload_new_artifact(gc, namespace_name, test_repo_name, "4.0.2", key, tags=["application"])

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        content_units = [
            collection_resp["results"][0]["pulp_href"],
            collection_resp["results"][1]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, results = search_collection_endpoint(
            gc, repository_name=test_repo_name, is_highest=is_highest
        )
        expected = [
            {"repo_name": test_repo_name, "cv_name": artifact_1.name, "cv_version": cv_version}
        ]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.parametrize("is_deprecated", [True, False])
    @pytest.mark.x_repo_search
    def test_search_by_is_deprecated_true_false(self, galaxy_client, is_deprecated):
        """
        Verifies that search endpoint can search by is_deprecated parameter
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)

        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        artifact_2 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "4.0.1", tags=["application"]
        )

        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        content_units = [
            collection_resp_1["results"][0]["pulp_href"],
            collection_resp_2["results"][0]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        deprecate_collection(gc, namespace_name, artifact_1.name, repository=test_repo_name)

        cv_name = artifact_1.name if is_deprecated else artifact_2.name

        matches, results = search_collection_endpoint(
            gc, is_deprecated=is_deprecated, repository_name=test_repo_name
        )
        expected = [{"cv_name": cv_name, "is_deprecated": is_deprecated}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.x_repo_search
    def test_search_by_tags(self, galaxy_client):
        """
        Verifies that search endpoint can search by tags
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)

        tag = f"tag{generate_random_string()}"
        tags = ["application", "test_tag_2", tag]

        artifact_1 = upload_new_artifact(gc, namespace_name, test_repo_name, "1.0.1", tags=tags)
        artifact_2 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "4.0.2", tags=["application"]
        )

        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        content_units = [
            collection_resp_1["results"][0]["pulp_href"],
            collection_resp_2["results"][0]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        matches, results = search_collection_endpoint(
            gc, tags="application,test_tag_2", repository_name=test_repo_name
        )
        expected = [{"cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)
        assert matches == 1
        matches, results = search_collection_endpoint(
            gc, tags="application,test_tag_3", repository_name=test_repo_name
        )
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_search_by_q(self, galaxy_client):
        """
        Verifies that search endpoint can search by q
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        key = generate_random_string()

        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", key, tags=["application"]
        )
        artifact_2 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "4.0.2", tags=["application"]
        )

        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        content_units = [
            collection_resp_1["results"][0]["pulp_href"],
            collection_resp_2["results"][0]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, results = search_collection_endpoint(gc, q=key, repository_name=test_repo_name)
        expected = [{"cv_name": artifact_1.name}]
        assert verify_repo_data(expected, results)
        assert matches == 1
        matches, results = search_collection_endpoint(
            gc, q=f"does-not-exist-{generate_random_string()}"
        )
        assert matches == 0

    @pytest.mark.parametrize("is_signed", [True, False])
    @pytest.mark.x_repo_search
    @pytest.mark.skipif(is_ocp_env(), reason="Content signing not enabled in AAP Operator")
    def test_search_by_is_signed_true_false(self, galaxy_client, is_signed):
        """
        Verifies that search endpoint can search by is_signed
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        artifact_2 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "4.0.2", tags=["application"]
        )

        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        content_units = [
            collection_resp_1["results"][0]["pulp_href"],
            collection_resp_2["results"][0]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        sign_collection(gc, collection_resp_1["results"][0]["pulp_href"], repo_pulp_href)
        cv_name = artifact_1.name if is_signed else artifact_2.name
        matches, results = search_collection_endpoint(
            gc, is_signed=is_signed, repository_name=test_repo_name
        )
        expected = [{"cv_name": cv_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.x_repo_search
    def test_search_by_distribution_id(self, galaxy_client):
        """
        Verifies that search endpoint can search by distribution_id
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.0", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        distribution_id = get_distribution_id(gc, test_repo_name)
        matches, results = search_collection_endpoint(gc, distribution=distribution_id)
        expected = [{"cv_name": artifact.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.x_repo_search
    def test_search_by_base_path(self, galaxy_client):
        """
        Verifies that search endpoint can search by base_path
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.0", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, results = search_collection_endpoint(gc, distribution_base_path=test_repo_name)
        expected = [{"cv_name": artifact.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

    @pytest.mark.x_repo_search
    def test_search_by_dependency(self, galaxy_client):
        """
        Verifies that search endpoint can search by dependency
        """
        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        dep_name = f"names.dep{generate_random_string()}"
        artifact = upload_new_artifact(
            gc,
            namespace_name,
            test_repo_name,
            "1.0.0",
            dependencies={dep_name: "1.0.0"},
            tags=["application"],
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        matches, results = search_collection_endpoint(gc, dependency=dep_name)
        expected = [{"cv_name": artifact.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 2  # staging (+1)

    @pytest.mark.x_repo_search
    def test_search_version_range(self, galaxy_client):
        """
        Verifies that search endpoint can search by version range
        """

        test_repo_name = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact_1 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "6.6.6", tags=["application"]
        )
        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1.name}"
        )

        artifact_2 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "8.8.8", tags=["application"]
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2.name}"
        )

        artifact_3 = upload_new_artifact(
            gc, namespace_name, test_repo_name, "12.6.6", tags=["application"]
        )
        collection_resp_3 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_3.name}"
        )
        content_units = [
            collection_resp_1["results"][0]["pulp_href"],
            collection_resp_2["results"][0]["pulp_href"],
            collection_resp_3["results"][0]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        matches, results = search_collection_endpoint(
            gc, version_range=">=6.6.6,<8.8.8", repository_name=test_repo_name
        )
        expected = [{"cv_name": artifact_1.name, "repo_name": test_repo_name}]
        assert verify_repo_data(expected, results)
        assert matches == 1

        matches, results = search_collection_endpoint(
            gc, version_range=">=6.6.6", repository_name=test_repo_name
        )
        expected = [
            {"cv_name": artifact_2.name, "repo_name": test_repo_name},
            {"cv_name": artifact_1.name, "repo_name": test_repo_name},
            {"cv_name": artifact_3.name, "repo_name": test_repo_name},
        ]
        assert verify_repo_data(expected, results)
        assert matches == 3

        matches, results = search_collection_endpoint(
            gc, version_range="<=8.8.8", repository_name=test_repo_name
        )
        expected = [
            {"cv_name": artifact_2.name, "repo_name": test_repo_name},
            {"cv_name": artifact_1.name, "repo_name": test_repo_name},
        ]
        assert verify_repo_data(expected, results)
        assert matches == 2

    @pytest.mark.x_repo_search
    def test_private_repo(self, galaxy_client):
        """
        Verifies that a basic user can't view private repos
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")

        repo_pulp_href = create_repo_and_dist(gc, test_repo_name, private=True)
        namespace_name = create_test_namespace(gc)
        key = generate_random_string()
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(gc, namespace_name, test_repo_name, "1.0.2", key, tags=["application"])

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [
            collection_resp["results"][0]["pulp_href"],
            collection_resp["results"][1]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        user, group = add_new_user_to_new_group(gc)
        gc_user = galaxy_client(user)
        # ansible.view_ansiblerepository views private repos too
        matches, result = search_collection_endpoint(
            gc_user, repository_name=test_repo_name, name=artifact.name
        )
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_any_user_can_see_non_private_repos(self, galaxy_client):
        """
        Verifies that a user without permissions can view repos that are not private
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")

        repo_pulp_href = create_repo_and_dist(gc, test_repo_name, private=False)
        namespace_name = create_test_namespace(gc)
        key = generate_random_string()
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(gc, namespace_name, test_repo_name, "1.0.2", key, tags=["application"])

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [
            collection_resp["results"][0]["pulp_href"],
            collection_resp["results"][1]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        user, group = add_new_user_to_new_group(gc)
        gc_user = galaxy_client(user)
        # ansible.view_ansiblerepository views private repos too
        matches, result = search_collection_endpoint(
            gc_user, repository_name=test_repo_name, name=artifact.name
        )
        assert matches == 2

    @pytest.mark.x_repo_search
    def test_private_repo_with_perm(self, galaxy_client):
        """
        Verifies that a user with view permissions can view private repos
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")

        repo_pulp_href = create_repo_and_dist(gc, test_repo_name, private=True)
        namespace_name = create_test_namespace(gc)
        key = generate_random_string()
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", key, tags=["application"]
        )
        upload_new_artifact(gc, namespace_name, test_repo_name, "1.0.2", key, tags=["application"])

        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [
            collection_resp["results"][0]["pulp_href"],
            collection_resp["results"][1]["pulp_href"],
        ]
        add_content_units(gc, content_units, repo_pulp_href)

        user, group = add_new_user_to_new_group(gc)
        permissions = ["ansible.view_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])

        gc_user = galaxy_client(user)
        # ansible.view_ansiblerepository views private repos too
        matches, result = search_collection_endpoint(
            gc_user, repository_name=test_repo_name, name=artifact.name
        )
        assert matches == 2

    @pytest.mark.x_repo_search
    def test_search_non_existing_repo(self, galaxy_client):
        """
        Verifies that there are no results when the repository does not exist
        """
        test_repo_name_1 = f"repo-test-1-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        namespace_name = create_test_namespace(gc)
        artifact_1v1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1v1.name}"
        )
        content_units_1 = [collection_resp_1["results"][0]["pulp_href"]]
        add_content_units(gc, content_units_1, repo_pulp_href_1)

        matches, _ = search_collection_endpoint(
            gc, repository_name=f"does-not-exist-{generate_random_string()}"
        )
        assert matches == 0

        matches, _ = search_collection_endpoint(
            gc, repository_name=f"does-not-exist-{generate_random_string()}", name=artifact_1v1.name
        )
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_search_collection_in_wrong_repo(self, galaxy_client):
        """
        Verifies that the search returns no matches when a collection is searched in the wrong repo
        """
        test_repo_name_1 = f"repo-test-1-{generate_random_string()}"
        test_repo_name_2 = f"repo-test-2-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        create_repo_and_dist(gc, test_repo_name_2)
        namespace_name = create_test_namespace(gc)
        artifact_1v1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp_1 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_1v1.name}"
        )
        content_units_1 = [collection_resp_1["results"][0]["pulp_href"]]
        add_content_units(gc, content_units_1, repo_pulp_href_1)
        matches, _ = search_collection_endpoint(
            gc, repository_name=test_repo_name_2, name=artifact_1v1.name
        )
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_search_after_deletion(self, galaxy_client):
        """
        Verifies that the search returns no matches when a collection has been deleted
        """
        test_repo_name_2 = f"repo-test-2-{generate_random_string()}"
        test_repo_name_3 = f"repo-test-3-{generate_random_string()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)
        repo_pulp_href_3 = create_repo_and_dist(gc, test_repo_name_3)
        namespace_name = create_test_namespace(gc)
        artifact_3v1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_2, "1.0.1", tags=["application"]
        )

        collection_resp_3 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_3v1.name}"
        )
        content_units_3 = [collection_resp_3["results"][0]["pulp_href"]]

        add_content_units(gc, content_units_3, repo_pulp_href_2)
        add_content_units(gc, content_units_3, repo_pulp_href_3)

        delete_collection(
            gc, namespace_name, artifact_3v1.name, version="1.0.1", repository=test_repo_name_3
        )
        matches, results = search_collection_endpoint(gc, name=artifact_3v1.name)
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_search_after_delete_repo_with_contents(self, galaxy_client):
        """
        Verifies a non-empty repo can be deleted and search returns 0
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("iqe_admin")
        repo_pulp_href = create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        collection_resp = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc, content_units, repo_pulp_href)
        delete_repository(gc, test_repo_name)
        repos = get_all_repositories(gc)
        assert not repo_exists(test_repo_name, repos)
        matches, results = search_collection_endpoint(
            gc, name=artifact.name, repository_name=test_repo_name
        )
        assert matches == 0

    @pytest.mark.x_repo_search
    def test_is_highest_per_repo(self, galaxy_client):
        """
        Verifies is_highest is per repo
        """
        test_repo_name_1 = f"repo-test-1-{generate_random_string()}"
        test_repo_name_2 = f"repo-test-2-{generate_random_string()}"

        gc = galaxy_client("iqe_admin")
        repo_pulp_href_1 = create_repo_and_dist(gc, test_repo_name_1)
        repo_pulp_href_2 = create_repo_and_dist(gc, test_repo_name_2)
        namespace_name = create_test_namespace(gc)
        key_2 = generate_random_string()
        upload_new_artifact(
            gc, namespace_name, test_repo_name_1, "1.0.2", key_2, tags=["application"]
        )
        artifact_2v1 = upload_new_artifact(
            gc, namespace_name, test_repo_name_2, "1.0.1", key_2, tags=["application"]
        )
        collection_resp_2 = gc.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact_2v1.name}"
        )
        content_units_1 = [collection_resp_2["results"][1]["pulp_href"]]
        content_units_2 = [collection_resp_2["results"][0]["pulp_href"]]

        add_content_units(gc, content_units_1, repo_pulp_href_1)
        add_content_units(gc, content_units_2, repo_pulp_href_2)

        _, results = search_collection_endpoint(gc, name=artifact_2v1.name)
        expected = [
            {
                "repo_name": test_repo_name_1,
                "cv_name": artifact_2v1.name,
                "cv_version": "1.0.2",
                "is_highest": True,
            },
            {
                "repo_name": test_repo_name_2,
                "cv_name": artifact_2v1.name,
                "cv_version": "1.0.1",
                "is_highest": True,
            },
        ]
        assert verify_repo_data(expected, results)
