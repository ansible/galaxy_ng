import pytest
import logging

from galaxy_ng.tests.integration.utils.repo_management_utils import (
    create_repo_and_dist,
    search_collection_endpoint,
    create_test_namespace,
    upload_new_artifact,
    add_content_units,
    remove_content_units,
)
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group

from galaxy_ng.tests.integration.utils.tools import generate_random_string
from galaxykit.remotes import (
    create_remote,
    view_remotes,
    update_remote,
    delete_remote,
    add_permissions_to_remote,
)
from galaxykit.repositories import (
    delete_repository,
    create_repository,
    patch_update_repository,
    put_update_repository,
    copy_content_between_repos,
    move_content_between_repos,
    add_permissions_to_repository,
    delete_distribution,
)
from galaxykit.utils import GalaxyClientError

logger = logging.getLogger(__name__)


@pytest.mark.min_hub_version("4.7dev")
class TestRBACRepos:
    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_create_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't create repositories
        """
        gc = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = [
            "galaxy.add_user",
            "galaxy.view_user",
        ]  # nothing to do with creating repos :P
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        test_repo_name = f"repo-test-{generate_random_string()}"
        with pytest.raises(GalaxyClientError) as ctx:
            create_repository(gc, test_repo_name)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_create_repo(self, galaxy_client):
        """
        Verifies that a user with permission can create repositories
        """
        gc = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["ansible.add_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        test_repo_name = f"repo-test-{generate_random_string()}"
        create_repo_and_dist(gc, test_repo_name)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't delete repositories
        """
        gc = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc)
        test_repo_name = f"repo-test-{generate_random_string()}"
        create_repository(gc, test_repo_name)  # test repo to be deleted
        permissions = [
            "ansible.add_ansiblerepository"
        ]  # nothing to do with deleting repos :P
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_repository(gc, test_repo_name)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_delete_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can delete repositories
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        test_repo_name = f"repo-test-{generate_random_string()}"
        create_repository(gc_admin, test_repo_name)  # test repo to be deleted
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        delete_repository(gc_user, test_repo_name)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(
            gc_user, namespace_name, test_repo_name, "0.0.1"
        )  # (needs upload_to_namespace)
        collection_resp = gc_user.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        with pytest.raises(GalaxyClientError) as ctx:
            add_content_units(
                gc_user, content_units, repo_pulp_href
            )  # (needs change_ansiblerepository)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_remove_from_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't remove cv from repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name, "0.0.1"
        )  # (needs upload_to_namespace)
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(
            gc_admin, content_units, repo_pulp_href
        )  # (needs change_ansiblerepository)
        with pytest.raises(GalaxyClientError) as ctx:
            remove_content_units(
                gc_user, content_units, repo_pulp_href
            )  # (needs change_ansiblerepository)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_upload_to_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = [
            "galaxy.upload_to_namespace",
            "ansible.modify_ansible_repo_content",
        ]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(
            gc_user, namespace_name, test_repo_name, "0.0.1"
        )  # to staging (upload_to_namespace)
        collection_resp = gc_user.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(
            gc_user, content_units, repo_pulp_href
        )  # (modify_ansible_repo_content)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_remove_from_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can remove from repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = [
            "galaxy.upload_to_namespace",
            "ansible.modify_ansible_repo_content",
        ]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name, "0.0.1"
        )  # to staging (upload_to_namespace)
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(
            gc_admin, content_units, repo_pulp_href
        )  # (modify_ansible_repo_content)
        remove_content_units(
            gc_user, content_units, repo_pulp_href
        )  # (needs change_ansiblerepository)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_patch_update_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can update repositories (patch)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"description": "updated description"}
        patch_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_patch_update_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't update repositories (patch)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"description": "updated description"}
        with pytest.raises(GalaxyClientError) as ctx:
            patch_update_repository(
                gc_user, resp["pulp_href"].split("/")[-2], updated_body
            )
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_put_update_repo(self, galaxy_client):
        """
        Verifies that a user with permissions can update repositories (put)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        put_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_put_update_repo(self, galaxy_client):
        """
        Verifies that a user without permissions can't update repositories (put)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        resp = create_repository(gc_admin, test_repo_name, description="old_description")
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        with pytest.raises(GalaxyClientError) as ctx:
            put_update_repository(gc_user, resp["pulp_href"].split("/")[-2], updated_body)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_any_user_can_use_x_repo_search_endpoint(self, galaxy_client):
        """
        Verifies that any user can search in repositories
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository", "galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        search_collection_endpoint(gc_user, repository_name=test_repo_name)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_copy_cv_endpoint(self, galaxy_client):
        """
        Verifies a user with permissions can use the copy cv endpoint
        """
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "0.0.1"
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        # new user
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.modify_ansible_repo_content"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)

        copy_content_between_repos(
            gc_user, content_units, repo_pulp_href_1, [repo_pulp_href_2]
        )

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_move_cv_endpoint(self, galaxy_client):
        """
        Verifies a user with permissions can use the move cv endpoint
        """
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "0.0.1"
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        # new user
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.modify_ansible_repo_content"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)

        move_content_between_repos(
            gc_user, content_units, repo_pulp_href_1, [repo_pulp_href_2]
        )

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_copy_cv_endpoint(self, galaxy_client):
        """
        Verifies a user without permissions can't use the copy cv endpoint
        """
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "0.0.1"
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        # new user
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            copy_content_between_repos(
                gc_user, content_units, repo_pulp_href_1, [repo_pulp_href_2]
            )
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_move_cv_endpoint(self, galaxy_client):
        """
        Verifies a user without permissions can't use the move cv endpoint
        """
        gc_admin = galaxy_client("iqe_admin")

        test_repo_name_1 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_1 = create_repo_and_dist(gc_admin, test_repo_name_1)

        namespace_name = create_test_namespace(gc_admin)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name_1, "0.0.1"
        )
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(gc_admin, content_units, repo_pulp_href_1)

        test_repo_name_2 = f"repo-test-{generate_random_string()}"
        repo_pulp_href_2 = create_repo_and_dist(gc_admin, test_repo_name_2)

        # new user
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            move_content_between_repos(
                gc_user, content_units, repo_pulp_href_1, [repo_pulp_href_2]
            )
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_add_remote_missing_role(self, galaxy_client):
        """
        Verifies a user without permissions can't create remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)

        test_remote_name = f"remote-test-{generate_random_string()}"
        with pytest.raises(GalaxyClientError) as ctx:
            create_remote(gc_user, test_remote_name, gc_admin.galaxy_root)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_add_remote(self, galaxy_client):
        """
        Verifies a user with permissions can create remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)

        permissions = ["ansible.add_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])

        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_user, test_remote_name, gc_admin.galaxy_root)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_view_remotes_missing_role(self, galaxy_client):
        """
        Verifies a user without permissions can't view remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            view_remotes(gc_user)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_view_remote_role(self, galaxy_client):
        """
        Verifies a user with permissions can view remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        view_remotes(gc_user)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_update_remote_missing_role(self, galaxy_client):
        """
        Verifies a user without permissions can't update remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            update_remote(gc_user, test_remote_name, "new_url", {})
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_update_remote(self, galaxy_client):
        """
        Verifies a user with permissions can update remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote", "ansible.change_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        update_remote(gc_user, test_remote_name, "http://new_url/", {})

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_delete_remote(self, galaxy_client):
        """
        Verifies a user with permissions can delete remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote", "ansible.delete_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        delete_remote(gc_user, test_remote_name)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_remote(self, galaxy_client):
        """
        Verifies a user without permissions can't delete remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.view_collectionremote"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_remote(gc_user, test_remote_name)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_manage_roles_remotes(self, galaxy_client):
        """
        Verifies a user without permissions can't add permissions to remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)

        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            add_permissions_to_remote(gc_user, test_remote_name, "role_name", [])
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_manage_roles_remotes(self, galaxy_client):
        """
        Verifies a user with permissions can add permissions to remotes
        """
        gc_admin = galaxy_client("iqe_admin")
        test_remote_name = f"remote-test-{generate_random_string()}"
        create_remote(gc_admin, test_remote_name, gc_admin.galaxy_root)
        user, group = add_new_user_to_new_group(gc_admin)

        permissions = [
            "ansible.view_collectionremote",
            "ansible.manage_roles_collectionremote",
        ]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])

        gc_user = galaxy_client(user)
        add_permissions_to_remote(
            gc_user, test_remote_name, "galaxy.collection_remote_owner", [group["name"]]
        )

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_upload_to_repo_object_role(self, galaxy_client):
        """
        Verifies that a user with permissions can upload to repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.modify_ansible_repo_content"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name, "0.0.1")
        gc_user = galaxy_client(user)
        collection_resp = gc_user.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(
            gc_user, content_units, repo_pulp_href
        )  # (modify_ansible_repo_content)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_upload_to_repo_object_role(self, galaxy_client):
        """
        Verifies that a user without permissions can't upload to repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        namespace_name = create_test_namespace(gc_admin)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        artifact = upload_new_artifact(gc_admin, namespace_name, test_repo_name, "0.0.1")
        gc_user = galaxy_client(user)
        collection_resp = gc_user.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        with pytest.raises(GalaxyClientError) as ctx:
            add_content_units(
                gc_user, content_units, repo_pulp_href
            )  # (modify_ansible_repo_content)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_update_repo_object_role(self, galaxy_client):
        """
        Verifies that a user with permissions can update a repository (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        put_update_repository(gc_user, repo_pulp_href.split("/")[-2], updated_body)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_update_repo_object_role(self, galaxy_client):
        """
        Verifies that a user without permissions can't update a repository (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        gc_user = galaxy_client(user)
        updated_body = {"name": test_repo_name, "description": "updated description"}
        with pytest.raises(GalaxyClientError) as ctx:
            put_update_repository(gc_user, repo_pulp_href.split("/")[-2], updated_body)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_delete_repo_object_role(self, galaxy_client):
        """
        Verifies that a user with permissions can delete a repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        gc_user = galaxy_client(user)
        delete_repository(gc_user, test_repo_name)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_repo_object_role(self, galaxy_client):
        """
        Verifies that a user without permissions can't delete a repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.change_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_repository(gc_user, test_repo_name)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_add_permissions_to_repo_object_role(self, galaxy_client):
        """
        Verifies that a user with permissions can
        add permissions to repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.manage_roles_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        gc_user = galaxy_client(user)
        add_permissions_to_repository(gc_user, test_repo_name, role_name, ["ns_group_for_tests"])

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_add_permissions_to_repo_object_role(self, galaxy_client):
        """
        Verifies that a user without permissions
        can't add permissions to repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            add_permissions_to_repository(
                gc_user, test_repo_name, role_name, ["ns_group_for_tests"]
            )
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_add_permissions_to_repo_object_role_global_role(self, galaxy_client):
        """
        Verifies that a user with permissions
        can add permissions to repositories (global permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.manage_roles_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        create_repo_and_dist(gc_admin, test_repo_name)
        gc_user = galaxy_client(user)
        add_permissions_to_repository(gc_user, test_repo_name, role_name, ["ns_group_for_tests"])

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_add_permissions_to_repo_object_role_global_role(
            self, galaxy_client
    ):
        """
        Verifies that a user without permissions
        can't add permissions to repositories (global permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        gc_admin.add_role_to_group(role_name, group["id"])
        create_repo_and_dist(gc_admin, test_repo_name)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            add_permissions_to_repository(
                gc_user, test_repo_name, role_name, ["ns_group_for_tests"]
            )
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    @pytest.mark.parametrize(
        "protected_repo",
        ["validated", "rh-certified", "community", "published", "rejected", "staging"],
    )
    def test_admin_protected_repos_cant_be_deleted(self, galaxy_client, protected_repo):
        """
        Verifies that protected repos can't be deleted
        """
        gc_admin = galaxy_client("iqe_admin")
        with pytest.raises(GalaxyClientError) as ctx:
            delete_repository(gc_admin, protected_repo)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    @pytest.mark.parametrize(
        "protected_dist",
        ["validated", "rh-certified", "community", "published", "rejected", "staging"],
    )
    def test_admin_protected_distributions_cant_be_deleted(
            self, galaxy_client, protected_dist
    ):
        """
        Verifies that protected distributions can't be deleted
        """
        gc_admin = galaxy_client("iqe_admin")
        with pytest.raises(GalaxyClientError) as ctx:
            delete_distribution(gc_admin, protected_dist)
        assert ctx.value.response.status_code == 403

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_role_remove_from_repo_object_role(self, galaxy_client):
        """
        Verifies that a user with permissions can remove from repositories (object permission)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = [
            "galaxy.upload_to_namespace",
            "ansible.modify_ansible_repo_content",
        ]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name, "0.0.1"
        )  # to staging (upload_to_namespace)
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(
            gc_admin, content_units, repo_pulp_href
        )  # (modify_ansible_repo_content)
        remove_content_units(
            gc_user, content_units, repo_pulp_href
        )  # (needs change_ansiblerepository)

    @pytest.mark.rbac_repos
    @pytest.mark.iqe_rbac_test
    def test_missing_role_remove_from_repo_object_role(self, galaxy_client):
        """
        Verifies that a user without permissions can't remove cv from repositories (object role)
        """
        test_repo_name = f"repo-test-{generate_random_string()}"
        gc_admin = galaxy_client("iqe_admin")
        user, group = add_new_user_to_new_group(gc_admin)
        permissions = ["ansible.delete_ansiblerepository"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "any_description", permissions)
        repo_pulp_href = create_repo_and_dist(gc_admin, test_repo_name)
        add_permissions_to_repository(
            gc_admin, test_repo_name, role_name, [group["name"]]
        )
        namespace_name = create_test_namespace(gc_admin)
        gc_user = galaxy_client(user)
        artifact = upload_new_artifact(
            gc_admin, namespace_name, test_repo_name, "0.0.1"
        )  # (needs upload_to_namespace)
        collection_resp = gc_admin.get(
            f"pulp/api/v3/content/ansible/collection_versions/?name={artifact.name}"
        )
        content_units = [collection_resp["results"][0]["pulp_href"]]
        add_content_units(
            gc_admin, content_units, repo_pulp_href
        )  # (needs change_ansiblerepository)
        with pytest.raises(GalaxyClientError) as ctx:
            remove_content_units(
                gc_user, content_units, repo_pulp_href
            )  # (needs change_ansiblerepository)
        assert ctx.value.response.status_code == 403
