import pytest
import logging

from galaxy_ng.tests.integration.api.test_repo_management import create_repo_and_dist, create_test_namespace, \
    upload_new_artifact, add_content_units, search_collection_endpoint
from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group

from galaxy_ng.tests.integration.utils.tools import generate_random_string
from galaxykit.collections import sign_collection
from galaxykit.remotes import create_remote, view_remotes, update_remote, delete_remote, add_permissions_to_remote
from galaxykit.repositories import delete_repository, create_repository, patch_update_repository, put_update_repository, \
    copy_content_between_repos, move_content_between_repos, add_permissions_to_repository, delete_distribution, \
    create_distribution
from galaxykit.utils import GalaxyClientError, wait_for_task

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.6dev")  # set correct min hub version
class TestRBACRepos:

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
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

    @pytest.mark.standalone_only
    def test_role_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace", "ansible.modify_ansible_repo_content"]
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
        add_content_units(gc_user, content_units, repo_pulp_href)  # (modify_ansible_repo_content)

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
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

    @pytest.mark.rbac_repos
    @pytest.mark.standalone_only
    def test_user_cannot_use_x_repo_search_endpoint(self, galaxy_client):
        """
        Verifies that a user with permissions can search in repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            search_collection_endpoint(gc_user, repository_name=test_repo_name)
        assert ctx.value.response.status_code == 403

        # all users can list repos, is it correct?

    # @pytest.mark.this
    @pytest.mark.standalone_only
    def test_copy(self, galaxy_client):
        """
        Verifies
        """
        # unsigned
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name_1, "0.0.1")
        collection_resp = gc_admin.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        copy_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        # verify cv is in both repos
        pass

    # @pytest.mark.this
    @pytest.mark.standalone_only
    def test_move(self, galaxy_client):
        """
        Verifies
        """
        # usigned
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name_1, "0.0.1")
        collection_resp = gc_admin.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        move_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        # verify cv is gone from source_repo
        pass

    # @pytest.mark.this
    @pytest.mark.standalone_only
    def test_copy_signed(self, galaxy_client):
        """
        Verifies
        """
        # signed
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name_1, "0.0.1")
        collection_resp = gc_admin.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        sign_collection(gc_admin, content_units[0], repo_pulp_href_1)

        copy_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        # verify cv is in both repos
        pass

    # @pytest.mark.this
    @pytest.mark.standalone_only
    def test_move_signed(self, galaxy_client):
        """
        Verifies
        """
        # signed
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name_1, "0.0.1")
        collection_resp = gc_admin.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        sign_collection(gc_admin, content_units[0], repo_pulp_href_1)

        move_content_between_repos(gc_admin, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        # verify cv is in both repos
        pass

    # @pytest.mark.this
    @pytest.mark.standalone_only
    def test_copy_rbac(self, galaxy_client):
        """
        Verifies
        """
        # unsigned
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name_1, "0.0.1")
        collection_resp = gc_admin.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        # new user
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)

        copy_content_between_repos(gc_user, content_units, repo_pulp_href_1, [repo_pulp_href_2])

    @pytest.mark.standalone_only
    def test_copy_missing_rbac_perm(self, galaxy_client):
        """
        Verifies
        """
        # unsigned
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name_1, "0.0.1")
        collection_resp = gc_admin.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        # new user
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            copy_content_between_repos(gc_user, content_units, repo_pulp_href_1, [repo_pulp_href_2])
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    @pytest.mark.this
    def test_remote(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_res = create_repository(gc_admin, test_repo_name_1, remote=test_remote_name)
        create_distribution(gc_admin, test_repo_name_1, repo_res['pulp_href'])

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_add_remote_missing_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)

        test_remote_name = f"remote-test-{generate_random_string()}"
        with pytest.raises(GalaxyClientError) as ctx:
            create_remote(gc_user, test_remote_name, gc_admin.galaxy_root)
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_add_remote_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)

        permissions = ["ansible.add_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])

        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_user, test_remote_name, gc_admin.galaxy_root)

    @pytest.mark.standalone_only
    def test_view_remote_role_missing_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            view_remotes(gc_user)
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_view_remote_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        view_remotes(gc_user)

    @pytest.mark.standalone_only
    @pytest.mark.this
    def test_update_remote_missing_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            update_remote(gc_user, test_remote_name, "new_url", {})
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_update_remote(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote", "ansible.change_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        update_remote(gc_user, test_remote_name, "http://new_url/", {})

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_delete_remote(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote", "ansible.delete_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        delete_remote(gc_user, test_remote_name)

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_delete_remote_missing_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_remote(gc_user, test_remote_name)
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_manage_roles_remotes_missing_role(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)

        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            add_permissions_to_remote(gc_user, test_remote_name, "role_name", [])
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    # @pytest.mark.this
    def test_manage_roles_remotes(self, galaxy_client):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)

        permissions = ["ansible.view_collectionremote", "ansible.manage_roles_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])

        gc_user = galaxy_client(user)
        add_permissions_to_remote(gc_user, test_remote_name, "galaxy.collection_remote_owner", [group["name"]])

######################################
    @pytest.mark.standalone_only
    def test_role_local_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.modify_ansible_repo_content"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name,
                                       "0.0.1")
        gc_user = galaxy_client(user)
        collection_resp = gc_user.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_user, content_units, repo_pulp_href)  # (modify_ansible_repo_content)

    @pytest.mark.standalone_only
    def test_role_missing_local_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name,
                                       "0.0.1")
        gc_user = galaxy_client(user)
        collection_resp = gc_user.get(f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}")
        content_units = [collection_resp["results"][0]["pulp_href"]]
        with pytest.raises(GalaxyClientError) as ctx:
            add_content_units(gc_user, content_units, repo_pulp_href)  # (modify_ansible_repo_content)
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    def test_role_local_update_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        put_update_repository(gc_user, repo_pulp_href.split("/")[-2], updated_body)

    @pytest.mark.standalone_only
    def test_role_local_missing_update_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        with pytest.raises(GalaxyClientError) as ctx:
            put_update_repository(gc_user, repo_pulp_href.split("/")[-2], updated_body)
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    def test_role_local_delete_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        gc_user = galaxy_client(user)
        # with pytest.raises(GalaxyClientError) as ctx:
        delete_repository(gc_user, test_repo_name)
        # assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    def test_role_local_missing_delete_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_repository(gc_user, test_repo_name)
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    def test_role_local_permissions_roles_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.manage_roles_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        gc_user = galaxy_client(user)
        add_permissions_to_repository(gc_user, test_repo_name, role_name, ["admin_staff"])

    @pytest.mark.standalone_only
    def test_role_local_missing_permissions_roles_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(gc_admin, test_repo_name, role_name, [group["name"]])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            add_permissions_to_repository(gc_user, test_repo_name, role_name, ["admin_staff"])
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    def test_role_global_permissions_roles_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.manage_roles_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        create_repo_and_dist(gc_admin, test_repo_name)
        gc_user = galaxy_client(user)
        add_permissions_to_repository(gc_user, test_repo_name, role_name, ["admin_staff"])

    @pytest.mark.standalone_only
    def test_role_global_missing_permissions_roles_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        create_repo_and_dist(gc_admin, test_repo_name)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            add_permissions_to_repository(gc_user, test_repo_name, role_name, ["admin_staff"])
        assert ctx.value.response.status_code == 403

    @pytest.mark.standalone_only
    @pytest.mark.parametrize("protected_repo", ["validated", "rh-certified", "community", "published", "rejected", "staging"])
    def test_admin_protected_repos(self, galaxy_client, protected_repo):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        with pytest.raises(GalaxyClientError) as ctx:
            delete_repository(gc_admin, protected_repo)
        assert ctx.value.response.status_code == 403

    @pytest.mark.this
    @pytest.mark.standalone_only
    @pytest.mark.parametrize("protected_dist", ["validated", "rh-certified", "community", "published", "rejected", "staging"])
    def test_admin_protected_distributions(self, galaxy_client, protected_dist):
        """
        Verifies
        """
        gc_admin = galaxy_client("iqe_admin")
        with pytest.raises(GalaxyClientError) as ctx:
            delete_distribution(gc_admin, protected_dist)
        assert ctx.value.response.status_code == 403