"""
(iqe) tests for rbac
Imported from https://gitlab.cee.redhat.com/insights-qe/iqe-automation-hub-plugin/
"""
import pytest

from galaxykit.collections import move_or_copy_collection
from galaxykit.container_images import delete_container as delete_image_container
from galaxykit.container_images import get_container_images
from galaxykit.containers import add_owner_to_ee
from galaxykit.containers import create_container
from galaxykit.containers import delete_container
from galaxykit.groups import create_group
from galaxykit.namespaces import delete_namespace
from galaxykit.registries import create_registry
from galaxykit.registries import delete_registry
from galaxykit.remotes import community_remote_config
from galaxykit.remotes import get_community_remote
from galaxykit.users import delete_user
from galaxykit.users import get_user
from galaxykit.users import update_user
from galaxykit.utils import GalaxyClientError

from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group, \
    create_test_user, create_local_image_container, create_namespace, \
    upload_test_artifact, collection_exists, user_exists


@pytest.mark.min_hub_version("4.6dev")
class TestRBAC:

    @pytest.mark.iqe_rbac_test
    def test_role_create_user(self, galaxy_client):
        """
        Verifies that when a user has the role to create users, the user can create users
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.add_user", "galaxy.view_user"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        create_test_user(gc)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_create_user(self, galaxy_client):
        """
        Verifies that when a user does not have the role to create users,
        the user can't create users
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.view_user"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            create_test_user(gc)
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_role_update_user(self, galaxy_client):
        """
        Verifies that when a user has the role to update users, the user can modify users
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.change_user", "galaxy.view_user"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        resp = get_user(gc_user, user["username"])
        resp["first_name"] = "changechangechange"
        resp["password"] = "changechangechange"
        update_user(gc_user, resp)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_update_user(self, galaxy_client):
        """
        Verifies that when a user does not have the role to update users,
        the user can't modify users
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.delete_user", "galaxy.view_user"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        resp = get_user(gc_user, user["username"])
        resp["first_name"] = "changechangechange"
        resp["password"] = "changechangechange"
        with pytest.raises(GalaxyClientError) as ctx:
            update_user(gc_user, resp)
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_role_delete_user(self, galaxy_client):
        """
        Verifies that when a user has the role to delete users, the user can delete users
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        user_to_delete = create_test_user(gc)
        permissions = ["galaxy.delete_user", "galaxy.view_user"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        delete_user(gc, user_to_delete["username"])
        assert not user_exists(user_to_delete["username"], gc)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_user(self, galaxy_client):
        """
        Verifies that when a user does not have the role to delete users,
        the user can't delete users
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        user_to_delete = create_test_user(gc)
        permissions = ["galaxy.add_user", "galaxy.view_user"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_user(gc, user_to_delete["username"])
        assert ctx.value.args[0] == 403
        assert user_exists(user_to_delete["username"], gc)

    @pytest.mark.iqe_rbac_test
    def test_can_create_group(self, galaxy_client):
        """
        Verifies that it's possible to create a group
        """
        group_name = f"rbac_test_group_{uuid4()}"
        group = galaxy_client("admin").create_group(group_name)
        assert group

    @pytest.mark.iqe_rbac_test
    def test_cannot_create_group_that_already_exists(self, galaxy_client):
        """
        Verifies that it's not possible to create a group that already exists
        """
        group_name = f"rbac_test_group_{uuid4()}"
        gc = galaxy_client("admin")
        create_group(gc, group_name)
        with pytest.raises(GalaxyClientError) as ctx:
            create_group(gc, group_name, exists_ok=False)
        assert ctx.value.args[0]["status"] == "409"

    @pytest.mark.iqe_rbac_test
    def test_admin_can_create_role(self, galaxy_client):
        """
        Verifies that an admin user can create a role
        """
        permissions = ["core.manage_roles_group"]
        gc = galaxy_client("admin")
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        resp = gc.create_role(role_name, "any_description", permissions)
        assert resp

    @pytest.mark.iqe_rbac_test
    def test_admin_cannot_create_duplicate_roles(self, galaxy_client):
        """
        Verifies that two roles cannot have the same name
        """
        permissions = ["core.manage_roles_group"]
        gc = galaxy_client("admin")
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        assert gc.create_role(role_name, "any_description", permissions)
        with pytest.raises(GalaxyClientError) as ctx:
            gc.create_role(role_name, "any_description", permissions)
        assert ctx.value.args[0] == 400

    @pytest.mark.iqe_rbac_test
    def test_can_delete_role(self, galaxy_client):
        """
        Verifies that it's possible to delete a role
        """
        permissions = ["core.manage_roles_group"]
        gc = galaxy_client("admin")
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.get_role(role_name)
        gc.delete_role(role_name)
        # verify that role is gone
        with pytest.raises(IndexError):
            gc.get_role(role_name)

    @pytest.mark.iqe_rbac_test
    def test_can_patch_update_role(self, galaxy_client):
        """
        Verifies that it's possible to patch update a role
        """
        permissions = ["core.manage_roles_group"]
        gc = galaxy_client("admin")
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        updated_body = {"description": "updated description"}
        gc.patch_update_role(role_name, updated_body)
        resp = gc.get_role(role_name)
        assert resp["description"] == "updated description"

    @pytest.mark.iqe_rbac_test
    def test_can_put_update_role(self, galaxy_client):
        """
        Verifies that it's possible to put update a role
        """
        permissions = ["core.manage_roles_group"]
        gc = galaxy_client("admin")
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        updated_body = {
            "name": role_name,
            "description": "updated description",
            "permissions": ["core.manage_roles_group"],
        }
        gc.put_update_role(role_name, updated_body)
        resp = gc.get_role(role_name)
        assert resp["description"] == "updated description"

    @pytest.mark.iqe_rbac_test
    def test_role_add_group(self, galaxy_client):
        """
        Verifies that when a user has the role to add groups, the user can create a group
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.add_group"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc = galaxy_client(user)
        new_group_name = f"new_group_{uuid4()}"
        gc.create_group(new_group_name)

    @pytest.mark.iqe_rbac_test
    def test_non_admin_cannot_create_roles(self, galaxy_client):
        """
        Verifies that a non admin user can't create roles
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        gc.add_user_to_group(user["username"], group["id"])
        permissions = [
            "galaxy.view_user",
            "galaxy.delete_user",
            "galaxy.add_user",
            "galaxy.change_user",
            "galaxy.view_group",
            "galaxy.delete_group",
            "galaxy.add_group",
            "galaxy.change_group",
        ]
        gc_user = galaxy_client(user)
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        with pytest.raises(GalaxyClientError) as ctx:
            gc_user.create_role(role_name, "any_description", permissions)
        assert ctx.value.args[0] == 403

    @pytest.mark.iqe_rbac_test
    def test_missing_permission_in_role_to_add_group(self, galaxy_client):
        """
        Verifies that when a user doesn't have the role to add groups,
        the user can't create a group
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        # incorrect permission to create a group (correct is galaxy.add_group)
        permissions = ["galaxy.view_group"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        new_group_name = f"rbac_test_group_{uuid4()}"
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            gc_user.create_group(new_group_name)
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_missing_role_permission_add_namespace(self, galaxy_client):
        """
        Verifies that when a user doesn't have the role to create a ns,
        the user can't create a ns
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = [
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
        ]  # incorrect permissions to add a namespace (correct is galaxy.add_namespace).
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            create_namespace(gc_user, group)
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_role_add_namespace(self, galaxy_client):
        """
        Verifies that when a user has the role to create a ns, the user can create a ns
        """
        gc = galaxy_client("admin")
        _, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.add_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        create_namespace(gc, group)

    @pytest.mark.iqe_rbac_test
    def test_role_delete_namespace(self, galaxy_client):
        """
        Verifies that when a user has the role to delete a ns, the user can delete a ns
        """
        gc = galaxy_client("admin")
        _, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.delete_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        namespace_name = create_namespace(gc, group=None)
        delete_namespace(gc, namespace_name)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_namespace(self, galaxy_client):
        """
        Verifies that when a user doesn't have the role to delete a ns,
        the user can't delete a ns
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.view_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        namespace_name = create_namespace(gc, group=None)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_namespace(gc_user, namespace_name)
        assert ctx.value.args[0] == 403

    @pytest.mark.iqe_rbac_test
    def test_object_role_upload_to_namespace(self, galaxy_client):
        """
        Verifies that when a user belongs to the same group as the one defined in a namespace
        and the role assigned to it gives permissions to upload a collection, the user can
        upload a collection even though the user does not have the (global)
        galaxy.upload_to_namespace permission
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        namespace_name = create_namespace(gc, group, object_roles=[role_name])
        gc_user = galaxy_client(user)
        upload_test_artifact(gc_user, namespace_name)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_upload_to_namespace(self, galaxy_client):
        """
        Verifies that when a user does not belong to the same group as the one defined in
        a namespace and the role assigned to it gives permissions to upload a collection,
        the user can't upload a collection even though the user has the
        galaxy.upload_to_namespace permission
        """
        gc = galaxy_client("admin")
        user, _ = add_new_user_to_new_group(gc)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)

        ns2_group_name = f"rbac_test_group_{uuid4()}"
        ns2_group = gc.create_group(ns2_group_name)
        ns2_name = create_namespace(gc, ns2_group, object_roles=[role_name])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            upload_test_artifact(gc_user, ns2_name)
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_global_role_upload_to_namespace(self, galaxy_client):
        """
        Verifies that when a user does not belong to the same group as the one defined in
        a namespace but has the upload_to_namespace permission assigned as a global role,
        the user can upload a collection
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        ns_name = create_namespace(gc, None)
        gc_user = galaxy_client(user)
        upload_test_artifact(gc_user, ns_name)

    @pytest.mark.iqe_rbac_test
    def test_global_role_delete_collection(self, galaxy_client):
        """
        Verifies that when a user has the role to delete collections,
        the user can delete collections
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["ansible.delete_collection"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        gc.add_role_to_group(role_name, group["id"])
        namespace_name = create_namespace(gc, None)
        artifact = upload_test_artifact(gc, namespace_name)
        move_or_copy_collection(gc, namespace_name, artifact.name, artifact.version)
        assert collection_exists(gc, namespace_name, artifact.name, artifact.version)
        gc_user = galaxy_client(user)
        gc_user.delete_collection(
            namespace_name, artifact.name, artifact.version, repository="published"
        )
        assert not collection_exists(gc, namespace_name, artifact.name, artifact.version)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_collection(self, galaxy_client):
        """
        Verifies that when a user doesn't have the permission to delete collections,
        the user cannot delete a collection
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        namespace_name = create_namespace(gc, group, object_roles=[role_name])
        artifact = upload_test_artifact(gc, namespace_name)
        move_or_copy_collection(gc, namespace_name, artifact.name, artifact.version)
        assert collection_exists(gc, namespace_name, artifact.name, artifact.version)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            gc_user.delete_collection(
                namespace_name, artifact.name, artifact.version, repository="published"
            )
        assert ctx.value.args[0]["status"] == "403"
        assert collection_exists(gc, namespace_name, artifact.name, artifact.version)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_reject_collection(self, galaxy_client):
        """
        Verifies that when a user does not have the role to reject collections,
        the user cannot reject a collection
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["galaxy.upload_to_namespace"]
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_name, "any_description", permissions)
        namespace_name = create_namespace(gc, group, object_roles=[role_name])
        artifact = upload_test_artifact(gc, namespace_name)
        move_or_copy_collection(gc, namespace_name, artifact.name, artifact.version)
        assert collection_exists(gc, namespace_name, artifact.name, artifact.version)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            # reject collection
            move_or_copy_collection(
                gc_user,
                namespace_name,
                artifact.name,
                artifact.version,
                source="published",
                destination="rejected",
            )
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_role_reject_collection(self, galaxy_client):
        """
        Verifies that when a user has role to reject collections,
        the user can reject a collection
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["ansible.modify_ansible_repo_content"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        permissions = ["galaxy.upload_to_namespace"]
        gc.create_role(role_name, "any_description", permissions)
        namespace_name = create_namespace(gc, group, object_roles=[role_name])
        artifact = upload_test_artifact(gc, namespace_name)
        move_or_copy_collection(gc, namespace_name, artifact.name, artifact.version)
        assert collection_exists(gc, namespace_name, artifact.name, artifact.version)
        gc_user = galaxy_client(user)
        move_or_copy_collection(
            gc_user,
            namespace_name,
            artifact.name,
            artifact.version,
            source="published",
            destination="rejected",
        )

    @pytest.mark.iqe_rbac_test
    def test_role_approve_collection(self, galaxy_client):
        """
        Verifies that when a user has role to approve collections,
        the user can approve a collection
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["ansible.modify_ansible_repo_content"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        permissions = ["galaxy.upload_to_namespace"]
        gc.create_role(role_name, "any_description", permissions)
        namespace_name = create_namespace(gc, group, object_roles=[role_name])
        artifact = upload_test_artifact(gc, namespace_name)
        gc_user = galaxy_client(user)
        move_or_copy_collection(
            gc_user, namespace_name, artifact.name, artifact.version
        )  # approve collection
        assert collection_exists(gc, namespace_name, artifact.name, artifact.version)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_approve_collection(self, galaxy_client):
        """
        Verifies that when a user does not have a role to approve collections,
        the user cannot approve a collection
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = []
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        role_name = f"galaxy.rbac_test_role_{uuid4()}"
        permissions = ["galaxy.upload_to_namespace"]
        gc.create_role(role_name, "any_description", permissions)
        namespace_name = create_namespace(gc, group, object_roles=[role_name])
        artifact = upload_test_artifact(gc, namespace_name)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            move_or_copy_collection(
                gc_user, namespace_name, artifact.name, artifact.version
            )  # approve collection
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_missing_role_add_remote_registry(self, galaxy_client):
        """
        Verifies that when a user does not have the role to add a remote registry,
        the user cannot add a remote registry
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["galaxy.add_group"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            create_registry(gc_user, f"remote_registry_{uuid4()}", "url")
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_role_add_remote_registry(self, galaxy_client):
        """
        Verifies that when a user does not have the role to add a remote registry,
        the user cannot add a remote registry
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["galaxy.add_containerregistryremote"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        create_registry(gc_user, f"remote_registry_{uuid4()}", "url")

    @pytest.mark.iqe_rbac_test
    def test_role_delete_remote_registry(self, galaxy_client):
        """
        Verifies that when a user has the role to delete a remote registry,
        the user can delete a remote registry
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["galaxy.delete_containerregistryremote"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        remote_registry = f"remote_registry_{uuid4()}"
        create_registry(gc, remote_registry, "url")
        gc_user = galaxy_client(user)
        delete_registry(gc_user, remote_registry)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_remote_registry(self, galaxy_client):
        """
        Verifies that when a user does not have the role to delete a remote registry,
        the user cannot delete a remote registry
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["galaxy.add_group"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        remote_registry = f"remote_registry_{uuid4()}"
        create_registry(gc, remote_registry, "url")
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_registry(gc_user, remote_registry)
        assert ctx.value.args[0] == 403

    @pytest.mark.iqe_rbac_test
    def test_role_add_ee(self, galaxy_client):
        """
        Verifies that when a user has the role to create an ee, the user can create an ee
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)

        permissions_user = ["container.add_containernamespace"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])

        # this block added for pulp 3.27 upgrade ...
        permissions_user = ["container.manage_roles_containernamespace"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description2", permissions_user)
        gc.add_role_to_group(role_user, group["id"])

        remote_registry = f"remote_registry_{uuid4()}"
        create_registry(gc, remote_registry, "url")
        gc_user = galaxy_client(user)
        ee_name = f"ee_{uuid4()}"
        create_container(gc_user, ee_name, "upstream_name", remote_registry)
        add_owner_to_ee(gc_user, ee_name, group["name"], [role_user])

    @pytest.mark.iqe_rbac_test
    def test_missing_role_add_ee(self, galaxy_client):
        """
        Verifies that when a user does not have the role to create ee, the user cannot create an ee
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["galaxy.add_group"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        remote_registry = f"remote_registry_{uuid4()}"
        create_registry(gc, remote_registry, "url")
        gc_user = galaxy_client(user)
        ee_name = f"ee_{uuid4()}"
        with pytest.raises(GalaxyClientError) as ctx:
            create_container(gc_user, ee_name, "upstream_name", remote_registry)
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_role_delete_ee(self, galaxy_client):
        """
        Verifies that when a user has the role to remove an ee, the user can remove an ee
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["container.delete_containerrepository"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        remote_registry = f"remote_registry_{uuid4()}"
        create_registry(gc, remote_registry, "url")
        ee_name = f"ee_{uuid4()}"
        create_container(gc, ee_name, "upstream_name", remote_registry)
        gc_user = galaxy_client(user)
        delete_container(gc_user, ee_name)

    @pytest.mark.iqe_rbac_test
    def test_missing_role_delete_ee(self, galaxy_client):
        """
        Verifies that when a user does not have the role to remove an ee,
        the user cannot remove an ee
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["galaxy.add_group"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        remote_registry = f"remote_registry_{uuid4()}"
        create_registry(gc, remote_registry, "url")
        ee_name = f"ee_{uuid4()}"
        create_container(gc, ee_name, "upstream_name", remote_registry)
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_container(gc_user, ee_name)
        assert ctx.value.args[0] == 403

    @pytest.mark.iqe_rbac_test
    def test_user_role_remotes(self, galaxy_client):
        """
        Verifies that a user with change collection remote permissions can config remotes
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["ansible.change_collectionremote"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        community_remote_config(gc_user, "http://google.com/", "username", "password")

    @pytest.mark.iqe_rbac_test
    def test_user_missing_role_remotes(self, galaxy_client):
        """
        Verifies that a user without change collection remote permissions can't config remotes
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = []
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        with pytest.raises(GalaxyClientError) as ctx:
            community_remote_config(gc_user, "http://google.com/", "username", "password")
        assert ctx.value.args[0]["status"] == "403"

    @pytest.mark.iqe_rbac_test
    def test_user_role_get_remotes(self, galaxy_client):
        """
        Verifies that a user with view remotes roles can view remote config
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions = ["ansible.view_collectionremote"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        get_community_remote(gc_user)

    @pytest.mark.iqe_rbac_test
    def test_missing_object_role_push_image_to_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user does not have
        object permissions to push an image, the user can't push an image
        """
        gc = galaxy_client("admin")
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        user, _ = add_new_user_to_new_group(gc)
        gc_user = galaxy_client(user)
        try:
            gc_user.push_image(ee_name + ":latest")
        except GalaxyClientError as e:
            # We expect the underlying podman command to fail, but we don't
            # want to accidentally catch any other error, so we check that
            # the error is the podman return code.
            assert "retcode" in str(e)

    @pytest.mark.iqe_rbac_test
    def test_object_role_push_image_to_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user has object permissions to push an image,
        the user can push an image
        """
        gc = galaxy_client("admin")
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        user, group = add_new_user_to_new_group(gc)
        permissions_user = ["container.namespace_push_containerdistribution"]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        add_owner_to_ee(gc, ee_name, group["name"], [role_user])
        gc_user = galaxy_client(user)
        gc_user.push_image(ee_name + ":latest")

    @pytest.mark.iqe_rbac_test
    def test_global_role_push_image_to_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user has global permissions
        to push an image, the user can push an image
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = [
            "container.add_containernamespace",
            "container.namespace_push_containerdistribution",
        ]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        gc_user = galaxy_client(user)
        gc_user.push_image(ee_name + ":latest")

    @pytest.mark.iqe_rbac_test
    def test_missing_global_role_push_image_to_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user does not have
        global permissions to push an image, the user can't push an image
        """
        gc = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc)
        permissions_user = []
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        gc_user = galaxy_client(user)
        try:
            gc_user.push_image(ee_name + ":latest")
        except GalaxyClientError as e:
            # We expect the underlying podman command to fail, but we don't
            # want to accidentally catch any other error, so we check that
            # the error is the podman return code.
            assert "retcode" in str(e)

    @pytest.mark.iqe_rbac_test
    def test_missing_object_role_delete_image_from_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user does not have
        object permissions to delete an image, the user can't delete an image
        """
        gc = galaxy_client("admin")
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        user, group = add_new_user_to_new_group(gc)
        permissions_user = [
            "container.add_containernamespace",
            "container.namespace_push_containerdistribution",
        ]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        add_owner_to_ee(gc, ee_name, group["name"], [role_user])
        gc_user = galaxy_client(user)
        gc_user.push_image(ee_name + ":latest")
        all_images = get_container_images(gc_user, ee_name)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_image_container(gc_user, ee_name, all_images["data"][0]["digest"])
        assert ctx.value.args[0] == 403

    @pytest.mark.iqe_rbac_test
    def test_global_role_delete_image_from_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user has
        global permissions to delete an image, the user can delete an image
        """
        gc = galaxy_client("admin")
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        user, group = add_new_user_to_new_group(gc)
        permissions_user = [
            "container.delete_containerrepository",
            "container.namespace_push_containerdistribution",
        ]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        gc_user.push_image(ee_name + ":latest")
        all_images = get_container_images(gc_user, ee_name)
        delete_image_container(gc_user, ee_name, all_images["data"][0]["digest"])

    @pytest.mark.iqe_rbac_test
    def test_missing_global_role_delete_image_from_ee(self, galaxy_client, ansible_config):
        """
        Verifies that when a user does not have
        global permissions to delete an image, the user can't delete an image
        """
        gc = galaxy_client("admin")
        ee_name = create_local_image_container(ansible_config("admin"), gc)
        user, group = add_new_user_to_new_group(gc)
        permissions_user = [
            "container.add_containernamespace",
            "container.namespace_push_containerdistribution",
        ]
        role_user = f"galaxy.rbac_test_role_{uuid4()}"
        gc.create_role(role_user, "any_description", permissions_user)
        gc.add_role_to_group(role_user, group["id"])
        gc_user = galaxy_client(user)
        gc_user.push_image(ee_name + ":latest")
        all_images = get_container_images(gc_user, ee_name)
        with pytest.raises(GalaxyClientError) as ctx:
            delete_image_container(gc_user, ee_name, all_images["data"][0]["digest"])
        assert ctx.value.args[0] == 403
