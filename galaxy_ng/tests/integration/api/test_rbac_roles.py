"""Tests related to RBAC roles.

See: https://issues.redhat.com/browse/AAH-957
"""
import logging
import pytest
import requests

from .rbac_actions.utils import (
    ADMIN_CREDENTIALS,
    ADMIN_PASSWORD,
    ADMIN_USER,
    API_ROOT,
    NAMESPACE,
    PASSWORD,
    create_group_with_user_and_role,
    create_user,
    gen_string,
    ReusableCollection
)

from .rbac_actions.auth import (
    view_groups, delete_groups, add_groups, change_groups,
    view_users, delete_users, add_users, change_users,
    view_role, delete_role, add_role, change_role,
)
from .rbac_actions.misc import view_tasks
from .rbac_actions.collections import (
    create_collection_namespace,
    # change_collection_namespace_object,  # non-admin users 403 100% of time
    change_collection_namespace,
    delete_collection_namespace,
    upload_collection_to_namespace,
    # upload_collection_to_namespace_object,
    delete_collection,
    configure_collection_sync,
    launch_collection_sync,
    view_sync_configuration,
    approve_collections,
    reject_collections,
    deprecate_collections,
    # deprecate_collections_object,
    undeprecate_collections,
    # undeprecate_collections_object,
)
from .rbac_actions.exec_env import (
    create_exec_env_remote,
    delete_exec_env,
    change_exec_env_desc,
    # change_exec_env_desc_object,
    change_exec_env_readme,
    # change_exec_env_readme_object,
    create_containers_under_existing_container_namespace,
    # create_containers_under_existing_container_namespace_object,
    # push_containers_to_existing_container_namespace,
    # push_containers_to_existing_container_namespace_object,
    # change_container_namespace,
    # change_container_namespace_object,
    # tag_untag_container_namespace,
    # tag_untag_container_namespace_object,
    sync_remote_container,
    # sync_remote_container_object,
    create_container_registry_remote,
    change_container_registry_remote,
    delete_container_registry_remote,
    # create_remote_container,
    index_exec_env,
)

log = logging.getLogger(__name__)

# Order is important, CRU before D actions
GLOBAL_ACTIONS = [

    # AUTHENTICATION
    add_groups,
    view_groups,
    change_groups,
    delete_groups,
    add_users,
    change_users,
    view_users,
    delete_users,
    add_role,
    change_role,
    view_role,
    delete_role,

    # COLLECTIONS
    create_collection_namespace,
    change_collection_namespace,
    delete_collection_namespace,
    upload_collection_to_namespace,
    delete_collection,
    configure_collection_sync,
    launch_collection_sync,
    view_sync_configuration,
    approve_collections,
    reject_collections,
    deprecate_collections,
    undeprecate_collections,

    # EEs
    # create_container_registry_remote,
    # change_container_registry_remote,
    # create_exec_env_remote,
    # sync_remote_container,
    # change_exec_env_desc,
    # change_exec_env_readme,
    # index_exec_env,
    # delete_exec_env,
    # delete_container_registry_remote,
    # create_containers_under_existing_container_namespace,

    # MISC
    view_tasks,
]
# OBJECT_ACTIONS = [
#     change_collection_namespace_object,
#     # upload_collection_to_namespace_object,
#     # deprecate_collections_object,
#     # undeprecate_collections_object,
#     # change_exec_env_desc_object,
#     # change_exec_env_readme_object,
#     # create_containers_under_existing_container_namespace_object,
#     # push_containers_to_existing_container_namespace_object,
#     # change_container_namespace_object,
#     # tag_untag_container_namespace_object,
#     # sync_remote_container_object,
# ]

ROLES_TO_TEST = {
    "galaxy.content_admin": {
        view_groups,
        view_tasks,
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,
        reject_collections,
        approve_collections,
        delete_collection,
        delete_collection_namespace,
        configure_collection_sync,
        view_sync_configuration,
        launch_collection_sync,
        deprecate_collections,
        undeprecate_collections,
        create_exec_env_remote,
        delete_exec_env,
        change_exec_env_desc,
        change_exec_env_readme,
        create_container_registry_remote,
        change_container_registry_remote,
        delete_container_registry_remote,
        index_exec_env,
        create_containers_under_existing_container_namespace,
        # push_containers_to_existing_container_namespace,
        # change_container_namespace,
        # change_container_namespace_object,
        # tag_untag_container_namespace,
        sync_remote_container,
        # create_remote_container,
    },
    "galaxy.collection_admin": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,  # non-admin users 403 100% of time
        delete_collection,
        delete_collection_namespace,
        configure_collection_sync,
        view_sync_configuration,
        launch_collection_sync,
        approve_collections,
        reject_collections,
        deprecate_collections,
        undeprecate_collections,
    },
    "galaxy.collection_publisher": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,  # non-admin users 403 100% of time
        # deprecate_collections,
        # undeprecate_collections,
    },
    "galaxy.collection_curator": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        configure_collection_sync,
        view_sync_configuration,
        launch_collection_sync,
        approve_collections,
        reject_collections,
    },
    "galaxy.collection_namespace_owner": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        change_collection_namespace,  # should only be object permissions
        # change_collection_namespace_object,  # non-admin users 403 100% of time
        # upload_collection_to_namespace_object,
        # deprecate_collections_object,
        # undeprecate_collections_object,
    },
    "galaxy.execution_environment_admin": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        # create_exec_env,
        change_exec_env_desc,
        change_exec_env_readme,
        delete_exec_env,
        create_containers_under_existing_container_namespace,
        # push_containers_to_existing_container_namespace,
        # change_container_namespace,
        # tag_untag_container_namespace,
        sync_remote_container,
        create_container_registry_remote,
        change_container_registry_remote,
        delete_container_registry_remote,
        # create_remote_container,
        index_exec_env,
    },
    "galaxy.execution_environment_publisher": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        change_exec_env_desc,
        change_exec_env_readme,
        create_containers_under_existing_container_namespace,
        # push_containers_to_existing_container_namespace,
        # change_container_namespace,
        # tag_untag_container_namespace,
        sync_remote_container,
        # create_exec_env,
    },
    "galaxy.execution_environment_namespace_owner": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        change_exec_env_desc,  # should only be object permissions
        change_exec_env_readme,  # should only be object permissions
        # change_exec_env_desc_object,
        # change_exec_env_readme_object,
        # create_containers_under_existing_container_namespace_object,
        # push_containers_to_existing_container_namespace_object,
        # change_container_namespace_object,
        # tag_untag_container_namespace_object,
        # sync_remote_container_object,
    },
    "galaxy.execution_environment_collaborator": {
        view_groups,
        view_sync_configuration,
        view_tasks,
        change_exec_env_desc,  # should only be object permissions
        change_exec_env_readme,  # should only be object permissions
        # change_exec_env_desc_object,
        # change_exec_env_readme_object,
        # push_containers_to_existing_container_namespace_object,
        # tag_untag_container_namespace_object,
        # sync_remote_container_object,
    },
    "galaxy.group_admin": {
        view_sync_configuration,
        view_tasks,
        view_groups,
        add_groups,
        change_groups,
        delete_groups,
    },
    "galaxy.user_admin": {
        view_sync_configuration,
        view_groups,
        view_tasks,
        add_users,
        view_users,
        change_users,
        delete_users,
    },
    "galaxy.task_admin": {
        view_sync_configuration,
        view_groups,
        view_tasks,
    }
}


@pytest.mark.role_rbac
@pytest.mark.parametrize("role", ROLES_TO_TEST)
def test_global_role_actions(role):
    extra = {
        "collection": ReusableCollection(gen_string())
    }

    USERNAME = f"{NAMESPACE}_user_{gen_string()}"

    user = create_user(USERNAME, PASSWORD)
    group = create_group_with_user_and_role(user, role)
    group_id = group['id']

    expected_allows = ROLES_TO_TEST[role]

    failures = []
    # Test global actions
    for action in GLOBAL_ACTIONS:
        expect_pass = action in expected_allows
        try:
            action(user, PASSWORD, expect_pass, extra)
        except AssertionError:
            failures.append(action.__name__)

    # cleanup user, group, foo collection
    requests.delete(f"{API_ROOT}_ui/v1/users/{user['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/groups/{group_id}/", auth=ADMIN_CREDENTIALS)

    # # Test object actions
    # for action in OBJECT_ACTIONS:
    #     expect_pass = action in expected_allows
    #     try:
    #         action(role, expect_pass)
    #     except AssertionError:
    #         failures.append(action.__name__)

    extra['collection'].cleanup()

    assert failures == []


# @pytest.mark.role_rbac
# def test_role_actions_for_admin():
#     failures = []
#     # Test global actions
#     for action in GLOBAL_ACTIONS:
#         try:
#             action(ADMIN_USER, ADMIN_PASSWORD, True)
#         except AssertionError:
#             failures.append(action.__name__)
#     assert failures == []
