"""
(iqe) tests for rbac
Imported from https://gitlab.cee.redhat.com/insights-qe/iqe-automation-hub-plugin/
"""
import pytest
import logging


from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group, \
    create_test_user, upload_test_artifact
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
        result = search_collection(gc, search_string=artifact.name)
        logger.debug(result)
