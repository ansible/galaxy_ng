import pytest
import logging
import time

from galaxy_ng.tests.integration.utils.iqe_utils import is_ocp_env
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
from galaxykit.repositories import (
    copy_content_between_repos,
    delete_distribution,
    delete_repository,
    move_content_between_repos,
)
from galaxykit.utils import GalaxyClientError

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.7dev")
class TestRepositories:
    @pytest.mark.all
    @pytest.mark.repositories
    def test_cant_upload_same_collection_same_repo(self, galaxy_client):
        """
        Verifies that the same collection / version cannot be uploaded to the same repo
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("partner_engineer")
        create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"]
        )
        with pytest.raises(GalaxyClientError) as ctx:
            upload_test_artifact(gc, namespace_name, test_repo_name, artifact)
        assert ctx.value.response.status_code == 400

        # Cleanup
        delete_repository(gc, test_repo_name)
        delete_distribution(gc, test_repo_name)

    @pytest.mark.all
    @pytest.mark.repositories
    def test_copy_cv_endpoint(self, galaxy_client):
        """
        Verifies a cv can be copied to a different repo
        """
        gc_admin = galaxy_client("partner_engineer")

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

        # Cleanup
        delete_repository(gc_admin, test_repo_name_1)
        delete_repository(gc_admin, test_repo_name_2)
        delete_distribution(gc_admin, test_repo_name_1)
        delete_distribution(gc_admin, test_repo_name_2)

    @pytest.mark.all
    @pytest.mark.repositories
    def test_move_cv_endpoint(self, galaxy_client):
        """
        Verifies a cv can be moved to a different repo
        """
        gc_admin = galaxy_client("partner_engineer")

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

        # FIXME - the POST call will often result in an error with the oci+insights profile ...
        # root:client.py:216 Cannot parse expected JSON response
        # (http://localhost:38080/api/automation-hub/pulp/api/v3/repositories/ansible/ansible/):
        # Post "http://pulp:55001/api/automation-hub/pulp/api/v3/repositories/ansible/ansible/":
        # read tcp 172.18.0.2:47338->172.18.0.3:55001: read: connection reset by peer
        repo_pulp_href_2 = None
        retries = 10
        for x in range(0, retries):
            try:
                repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)
                break
            except Exception as e:
                print(e)
                time.sleep(5)

        if repo_pulp_href_2 is None:
            raise Exception("failed to create repo and dist")

        # FIXME - the POST call will often result in an error with the oci+insights profile ...
        # root:client.py:216 Cannot parse expected JSON response
        # (http://localhost:38080/api/<prefix>/pulp/api/v3/repositories/ansible/ansible/
        #   <uuid>/move_collection_version/):
        # Post "http://pulp:55001/api/<prefix>/pulp/api/v3/repositories/ansible/ansible/
        #   <uuid>/move_collection_version/":
        # readfrom tcp 172.18.0.3:37490->172.18.0.2:55001:
        #   write tcp 172.18.0.3:37490->172.18.0.2:55001: use of closed network connection
        retries = 10
        for x in range(0, retries):
            try:
                move_content_between_repos(
                    gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2]
                )
                break
            except Exception as e:
                print(e)
                time.sleep(5)

        # verify cv is only in destination repo
        _, results = search_collection_endpoint(gc_admin, name=artifact.name)
        expected = [{"cv_name": artifact.name, "repo_name": test_repo_name_2, "is_signed": False}]
        assert verify_repo_data(expected, results)
        matches, _ = search_collection_endpoint(
            gc_admin, name=artifact.name, repository_name=test_repo_name_1
        )
        assert matches == 0

        # Cleanup
        delete_repository(gc_admin, test_repo_name_1)
        delete_repository(gc_admin, test_repo_name_2)
        delete_distribution(gc_admin, test_repo_name_1)
        delete_distribution(gc_admin, test_repo_name_2)

    @pytest.mark.repositories
    @pytest.mark.deployment_standalone
    @pytest.mark.skipif(is_ocp_env(), reason="Content signing not enabled in AAP Operator")
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

        # Cleanup
        delete_repository(gc_admin, test_repo_name_1)
        delete_repository(gc_admin, test_repo_name_2)
        delete_distribution(gc_admin, test_repo_name_1)
        delete_distribution(gc_admin, test_repo_name_2)

    @pytest.mark.repositories
    @pytest.mark.deployment_standalone
    @pytest.mark.skipif(is_ocp_env(), reason="Content signing not enabled in AAP Operator")
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
        # Cleanup
        delete_repository(gc_admin, test_repo_name_1)
        delete_repository(gc_admin, test_repo_name_2)
        delete_distribution(gc_admin, test_repo_name_1)
        delete_distribution(gc_admin, test_repo_name_2)

    @pytest.mark.all
    @pytest.mark.repositories
    def test_directly_to_repo(self, galaxy_client):
        """
        Verifies that a collection can be uploaded directly to a custom repo
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("partner_engineer")
        create_repo_and_dist(gc, test_repo_name)
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"], direct_upload=True
        )
        matches, _ = search_collection_endpoint(gc, name=artifact.name)
        assert matches == 1
        # Cleanup
        delete_repository(gc, test_repo_name)
        delete_distribution(gc, test_repo_name)

    @pytest.mark.all
    @pytest.mark.repositories
    def test_cannot_directly_to_repo_if_pipeline_approved(self, galaxy_client):
        """
        Verifies that a collection can't be uploaded directly to a custom repo
        if pipeline is approved
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("partner_engineer")
        create_repo_and_dist(gc, test_repo_name, pipeline="approved")
        namespace_name = create_test_namespace(gc)
        with pytest.raises(GalaxyClientError) as ctx:
            upload_new_artifact(
                gc,
                namespace_name,
                test_repo_name,
                "1.0.1",
                tags=["application"],
                direct_upload=True,
            )
        assert ctx.value.response.status_code == 403
        # Cleanup
        delete_repository(gc, test_repo_name)
        delete_distribution(gc, test_repo_name)

    @pytest.mark.all
    @pytest.mark.repositories
    def test_can_directly_to_repo_if_pipeline_staging(self, galaxy_client):
        """
        Verifies that a collection can be uploaded directly to a custom repo
        if pipeline is staging
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc = galaxy_client("partner_engineer")
        create_repo_and_dist(gc, test_repo_name, pipeline="staging")
        namespace_name = create_test_namespace(gc)
        artifact = upload_new_artifact(
            gc, namespace_name, test_repo_name, "1.0.1", tags=["application"], direct_upload=True
        )
        matches, _ = search_collection_endpoint(gc, name=artifact.name)
        assert matches == 1

        # Cleanup
        delete_repository(gc, test_repo_name)
        delete_distribution(gc, test_repo_name)
