import pytest
import logging

from galaxy_ng.tests.integration.utils.rbac_utils import upload_test_artifact

from galaxy_ng.tests.integration.utils.repo_management_utils import (
    create_repo_and_dist,
    create_test_namespace,
    upload_new_artifact,
    add_content_units,
    search_collection_endpoint,
    verify_repo_data,
)
from galaxy_ng.tests.integration.utils.tools import generate_random_string
from galaxykit.collections import sign_collection
from galaxykit.repositories import copy_content_between_repos, move_content_between_repos
from galaxykit.utils import GalaxyClientError

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.7dev")
class TestRepositories:
    @pytest.mark.repositories
    def test_cant_upload_same_collection_same_repo(self, galaxy_client):
        """
        Verifies that the same collection / version cannot be uploaded to the same repo
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("admin")
        create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        with pytest.raises(GalaxyClientError) as ctx:
            upload_test_artifact(gc, namespace_name, test_repo_name, artifact)
        assert ctx.value.response.status_code == 400

    @pytest.mark.repositories
    def test_copy_cv_endpoint(self, galaxy_client):
        """
        Verifies a cv can be copied to a different repo
        """
        gc_admin = galaxy_client("admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        copy_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        # verify cv is in both
        matches, results = search_collection_endpoint(gc_admin, name=artifact.name)
        expected = [
            {"cv_name": artifact.name, "repo_name": test_repo_name_1, "is_signed": False},
            {"cv_name": artifact.name, "repo_name": test_repo_name_2, "is_signed": False},
        ]
        assert verify_repo_data(expected, results)

    @pytest.mark.repositories
    def test_move_cv_endpoint(self, galaxy_client):
        """
        Verifies a cv can be moved to a different repo
        """
        gc_admin = galaxy_client("admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        move_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        # verify cv is only in destination repo
        _, results = search_collection_endpoint(gc_admin, name=artifact.name)
        expected = [{"cv_name": artifact.name, "repo_name": test_repo_name_2, "is_signed": False}]
        assert verify_repo_data(expected, results)
        matches, _ = search_collection_endpoint(
            gc_admin, name=artifact.name, repository_name=test_repo_name_1
        )
        assert matches == 0

    @pytest.mark.repositories
    @pytest.mark.standalone_only
    def test_copy_signed_cv_endpoint(self, galaxy_client):
        """
        Verifies a signed cv can be copied to a different repo
        """
        gc_admin = galaxy_client("admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        sign_collection(gc_admin, content_units[0], repo_pulp_href_1)

        copy_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        matches, results = search_collection_endpoint(gc_admin, name=artifact.name)
        expected = [
            {"cv_name": artifact.name, "repo_name": test_repo_name_1, "is_signed": True},
            {"cv_name": artifact.name, "repo_name": test_repo_name_2, "is_signed": True},
        ]
        assert verify_repo_data(expected, results)

    @pytest.mark.repositories
    @pytest.mark.standalone_only
    def test_move_signed_cv_endpoint(self, galaxy_client):
        """
        Verifies a signed cv can be moved to a different repo
        """
        gc_admin = galaxy_client("admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "1.0.1", tags=["application"]
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        sign_collection(gc_admin, content_units[0], repo_pulp_href_1)

        move_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        _, results = search_collection_endpoint(gc_admin, name=artifact.name)
        expected = [{"cv_name": artifact.name, "repo_name": test_repo_name_2, "is_signed": True}]
        assert verify_repo_data(expected, results)
        matches, _ = search_collection_endpoint(
            gc_admin, name=artifact.name, repository_name=test_repo_name_1
        )
        assert matches == 0
