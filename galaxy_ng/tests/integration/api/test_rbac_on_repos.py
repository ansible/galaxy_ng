import pytest
import logging

from galaxy_ng.tests.integration.api.test_repo_management import create_repo_and_dist, create_test_namespace, \
    upload_new_artifact, add_content_units
from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group

from galaxy_ng.tests.integration.utils.tools import generate_random_string
from galaxykit.repositories import delete_repository, create_repository, patch_update_repository, put_update_repository
from galaxykit.utils import GalaxyClientError

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.6dev")  # set correct min hub version
class TestRBACRepos:

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_missing_role_create_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't create repositories
        """
        gc = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.add_user", "galaxy.view_user"]  # nothing to do with creating repos :P
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        test_repo_name = f"repo-test-{generate_random_string()}"
        with pytest.raises(GalaxyClientError) as ctx:
            create_repository(gc, test_repo_name)
        assert ctx.value.response.status_code == 403

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_role_create_repo(self, galaxy_client):
        """
        Verifies that a user with permission can create repositories
        """
        gc = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["ansible.add_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        test_repo_name = f"repo-test-{generate_random_string()}"
        # create_repository(gc, test_repo_name)
        create_repo_and_dist(gc, test_repo_name)

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_missing_role_delete_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't delete repositories
        """
        gc = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc)
        test_repo_name = f"repo-test-{generate_random_string()}"
        create_repository(gc, test_repo_name)  # test repo to be deleted
        permissions = ["ansible.add_ansiblerepository"]  # nothing to do with deleting repos :P
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_repository(gc, test_repo_name)
        assert ctx.value.response.status_code == 403

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_role_delete_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can delete repositories
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        test_repo_name = f"repo-test-{generate_random_string()}"
        create_repository(gc_admin, test_repo_name)  # test repo to be deleted
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        delete_repository(gc_user, test_repo_name)

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_missing_role_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(gc_user, namespace_name, test_repo_name, "0.0.1")  # (needs upload_to_namespace)
        collection_resp = gc_user.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        with pytest.raises(GalaxyClientError) as ctx:
            add_content_units(gc_user, content_units, repo_pulp_href)  # (needs change_ansiblerepository)
        assert ctx.value.response.status_code == 403

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_role_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(gc_user, namespace_name, test_repo_name,
                                       "0.0.1")  # to staging (upload_to_namespace)
        collection_resp = gc_user.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_user, content_units, repo_pulp_href)  # (change_ansiblerepository)

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_role_patch_update_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can update a repositories (patch)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"description": "updated description"}
        patch_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_missing_role_patch_update_repo(self, galaxy_client):
        """
        Verifies
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"description": "updated description"}
        with pytest.raises(GalaxyClientError) as ctx:
            patch_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)
        assert ctx.value.response.status_code == 403

    # @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_role_put_update_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can update a repositories (put)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        put_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)

    @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_missing_role_put_update_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't update a repositories (put)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        with pytest.raises(GalaxyClientError) as ctx:
            put_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)
        assert ctx.value.response.status_code == 403

        # all users can list repos, is it correct?
