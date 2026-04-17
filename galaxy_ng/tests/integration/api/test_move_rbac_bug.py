"""Test for AAP-70914: move collection with object-level permissions fails with 403."""

import pytest
from orionutils.generator import build_collection

from galaxykit.collections import upload_artifact
from galaxykit.utils import wait_for_task, wait_for_url, GalaxyClientError
from galaxy_ng.tests.integration.utils.rbac_utils import add_new_user_to_new_group
from galaxykit.repositories import add_permissions_to_repository
from galaxy_ng.tests.integration.utils.tools import generate_random_string
from ..constants import USERNAME_PUBLISHER


@pytest.fixture
def staged_collection(galaxy_client):
    """Upload a collection to staging repo and wait for it to be available."""
    gc_admin = galaxy_client("admin")
    namespace = USERNAME_PUBLISHER

    artifact = build_collection("skeleton", config={"namespace": namespace, "tags": ["test"]})
    resp = upload_artifact(None, gc_admin, artifact)
    wait_for_task(gc_admin, resp)

    dest_url = (
        f"content/staging/v3/plugin/ansible/content/staging/collections/"
        f"index/{namespace}/{artifact.name}/versions/{artifact.version}/"
    )
    wait_for_url(gc_admin, dest_url)

    return artifact


@pytest.mark.min_hub_version("4.7dev")
class TestMoveV3RBAC:
    """Tests for AAP-70914: v3 move endpoint with object-level permissions"""

    @pytest.mark.rbac_repos
    @pytest.mark.deployment_standalone
    @pytest.mark.parametrize(
        ("action", "grant_perms", "expected_status"),
        [
            ("move", True, 202),
            ("move", False, 403),
            ("copy", True, 202),
            ("copy", False, 403),
        ],
    )
    def test_v3_endpoint_object_level_perms(
        self, galaxy_client, staged_collection, action, grant_perms, expected_status
    ):
        """
        Verifies v3 move/copy endpoints work with object-level permissions.

        Bug: AAP-70914
        - User has galaxy.ansible_repository_owner on staging + published (object-level)
        - GUI: can approve ✓
        - API: POST /v3/collections/.../move/staging/published/ → 403 ✗

        Root cause: standalone.py uses has_model_perms (global only) instead of
        v3_can_copy_or_move (object-level)
        """
        gc_admin = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc_admin)

        if grant_perms:
            # Create role and grant object-level permissions on both repos
            permissions = ["ansible.modify_ansible_repo_content"]
            role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
            gc_admin.create_role(role_name, "Role for object-level permissions test", permissions)

            add_permissions_to_repository(gc_admin, "staging", role_name, [group["name"]])
            add_permissions_to_repository(gc_admin, "published", role_name, [group["name"]])

        # Try to move/copy as test user using v3 API
        gc_user = galaxy_client(user)
        endpoint_url = (
            f"v3/collections/{staged_collection.namespace}/"
            f"{staged_collection.name}/versions/{staged_collection.version}/"
            f"{action}/staging/published/"
        )

        if expected_status >= 400:
            # galaxykit raises GalaxyClientError for error responses
            with pytest.raises(GalaxyClientError) as ctx:
                gc_user.post(endpoint_url, body={})
            assert ctx.value.response.status_code == expected_status, (
                f"Expected {expected_status}, got {ctx.value.response.status_code}. "
                f"User {'with' if grant_perms else 'without'} permissions "
                f"should {'succeed' if grant_perms else 'fail'} on {action}"
            )
        else:
            response = gc_user.post(endpoint_url, body={}, parse_json=False)
            assert response.status_code == expected_status, (
                f"Expected {expected_status}, got {response.status_code}. "
                f"User {'with' if grant_perms else 'without'} permissions "
                f"should {'succeed' if grant_perms else 'fail'} on {action}"
            )

    @pytest.mark.rbac_repos
    @pytest.mark.deployment_standalone
    def test_global_permission_move_v3_endpoint(self, galaxy_client, staged_collection):
        """
        Verifies that a user with global (model-level) permissions can still use move endpoint.

        Regression test: After changing from has_model_perms to v3_can_copy_or_move,
        users with global permissions should still work (short-circuit at line 381).
        """
        gc_admin = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc_admin)

        # Create role with required permission
        permissions = ["ansible.modify_ansible_repo_content"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "Role for object-level permissions test", permissions)

        # Grant GLOBAL permission (not object-level)
        gc_admin.add_role_to_group(role_name, group["id"])

        # Try to move as test user (global permissions) using v3 API
        gc_user = galaxy_client(user)
        move_url = (
            f"v3/collections/{staged_collection.namespace}/"
            f"{staged_collection.name}/versions/{staged_collection.version}/"
            f"move/staging/published/"
        )

        # Should succeed with global permissions
        response = gc_user.post(move_url, body={}, parse_json=False)
        assert response.status_code == 202, (
            f"Expected 202, got {response.status_code}. "
            f"User with global permissions should be able to move collections"
        )

    @pytest.mark.rbac_repos
    @pytest.mark.deployment_standalone
    @pytest.mark.parametrize("repo_with_perms", ["staging", "published"])
    def test_partial_permission_move_v3_endpoint(
        self, galaxy_client, staged_collection, repo_with_perms
    ):
        """
        Verifies that a user with permissions on only one repo (source OR dest) gets 403.

        User has object-level permissions on only staging OR only published.
        Should fail with 403 because both repos need permission.
        """
        gc_admin = galaxy_client("admin")
        user, group = add_new_user_to_new_group(gc_admin)

        # Create role with required permission
        permissions = ["ansible.modify_ansible_repo_content"]
        role_name = f"galaxy.rbac_test_role_{generate_random_string()}"
        gc_admin.create_role(role_name, "Role for object-level permissions test", permissions)

        # Grant object-level permissions on ONLY one repo (source OR dest)
        add_permissions_to_repository(gc_admin, repo_with_perms, role_name, [group["name"]])

        # Try to move as test user (permissions only on one repo)
        gc_user = galaxy_client(user)
        move_url = (
            f"v3/collections/{staged_collection.namespace}/"
            f"{staged_collection.name}/versions/{staged_collection.version}/"
            f"move/staging/published/"
        )

        # Should fail because user lacks permissions on both repos
        # galaxykit raises GalaxyClientError for error responses
        with pytest.raises(GalaxyClientError) as ctx:
            gc_user.post(move_url, body={})
        assert ctx.value.response.status_code == 403, (
            f"Expected 403, got {ctx.value.response.status_code}. "
            f"User with permissions on only {repo_with_perms} should not be able to move"
        )
