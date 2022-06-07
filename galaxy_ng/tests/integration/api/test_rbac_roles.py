"""Tests related to RBAC roles.

See: https://issues.redhat.com/browse/AAH-957
"""
import logging
import pytest

from .rbac_actions.utils import (
    NAMESPACE,
    PASSWORD,
    create_group_with_user_and_role,
    create_user,
    gen_string,
)

from .rbac_actions.auth import (
    view_groups, delete_groups, add_groups, change_groups,
    view_users, delete_users, add_users, change_users,
    view_role, delete_role, add_role, change_role,
)
from .rbac_actions.misc import view_tasks  # , cancel_tasks
from .rbac_actions.collections import (
    create_collection_namespace,
    # create_collection_namespace_object,
    change_collection_namespace,
    delete_collection_namespace,
    configure_collection_sync,
    launch_collection_sync,
    view_sync_configuration,
    deprecate_collections,
    # deprecate_collections_object,
    undeprecate_collections,
    # undeprecate_collections_object,
    # upload_collection_to_namespace,
    # upload_collection_to_namespace_object,
)
from .rbac_actions.exec_env import (
    create_exec_env,
    delete_exec_env,
    change_exec_env_desc,
    change_exec_env_readme,
    # create_containers_under_existing_container_namespace,
    # push_containers_to_existing_container_namespace,
    # change_container_namespace,
    # change_container_namespace_object,
    # tag_untag_container_namespace,
    # sync_remote_container,
    create_container_registry_remote,
    change_container_registry_remote,
    delete_container_registry_remote,
    # create_remote_container,
    index_exec_env,
)

log = logging.getLogger(__name__)


GLOBAL_ACTIONS = [
    view_groups,
    delete_groups,
    add_groups,
    change_groups,
    view_users,
    delete_users,
    add_users,
    change_users,
    view_role,
    delete_role,
    add_role,
    change_role,
    view_tasks,
    # cancel_tasks,
    create_collection_namespace,
    # create_collection_namespace_object,
    change_collection_namespace,
    delete_collection_namespace,
    configure_collection_sync,
    launch_collection_sync,
    view_sync_configuration,
    deprecate_collections,
    # deprecate_collections_object,
    undeprecate_collections,
    # undeprecate_collections_object,
    # upload_collection_to_namespace,
    # upload_collection_to_namespace_object,
    # EE actions requiring account
    # create_container_registry_remote,
    # change_container_registry_remote,
    # delete_container_registry_remote,
    # create_exec_env,
    # delete_exec_env,
    # change_exec_env_desc,
    # change_exec_env_readme,
    # index_exec_env,
]
# OBJECT_ACTIONS = [
#     create_collection_namespace_object,
#     upload_collection_to_namespace_object,
#     deprecate_collections_object,
#     undeprecate_collections_object,
# ]
ROLES_TO_TEST = {
    "galaxy.content_admin": {
        view_groups,  # error?
        view_tasks,  # error?
        create_collection_namespace,
        change_collection_namespace,
        delete_collection_namespace,
        # upload_collection_to_namespace,
        # delete_collection,
        configure_collection_sync,
        launch_collection_sync,
        view_sync_configuration,
        # approve_reject_collections,
        deprecate_collections,
        undeprecate_collections,
        # EE actions requiring account
        # create_exec_env,
        # delete_exec_env,
        # change_exec_env_desc,
        # change_exec_env_readme,
        # create_container_registry_remote,
        # change_container_registry_remote,
        # delete_container_registry_remote,
        # index_exec_env,
        # EE subprocess-based actions
        # create_containers_under_existing_container_namespace,
        # push_containers_to_existing_container_namespace,
        # change_container_namespace,
        # change_container_namespace_object,
        # tag_untag_container_namespace,
        # sync_remote_container,
        # create_remote_container,
    },
    "galaxy.collection_admin": {
        view_groups,  # error?
        view_tasks,  # error?
        create_collection_namespace,
        change_collection_namespace,
        delete_collection_namespace,
        # upload_collection_to_namespace,
        # delete_collection,
        configure_collection_sync,
        launch_collection_sync,
        view_sync_configuration,
        # approve_reject_collections,
        deprecate_collections,
        undeprecate_collections,
    },
    "galaxy.collection_publisher": {
        view_groups,  # error?
        view_tasks,  # error?
        view_sync_configuration,  # error?
        create_collection_namespace,
        change_collection_namespace,
        # upload_collection_to_namespace,
    },
    "galaxy.collection_curator": {
        view_sync_configuration,  # error?
        view_groups,  # error?
        view_tasks,  # error?
        configure_collection_sync,
        launch_collection_sync,
        # view_collection_sync,
        # approve_reject_collections,
    },
    "galaxy.collection_namespace_owner": {
        view_sync_configuration,  # error?
        view_groups,  # error?
        view_tasks,  # error?
        change_collection_namespace,
        # upload_collection_to_namespace,
    },
    "galaxy.group_admin": {
        view_sync_configuration,  # error?
        view_tasks,  # error?
        view_groups,
        delete_groups,
        add_groups,
        change_groups,
    },
    "galaxy.user_admin": {
        view_sync_configuration,  # error?
        view_groups,  # error?
        view_tasks,  # error?
        view_users,
        delete_users,
        add_users,
        change_users,
    },
    "galaxy.task_admin": {
        view_sync_configuration,  # error?
        view_groups,  # error?
        view_tasks,
        # cancel_tasks,
    }
}


@pytest.mark.role_rbac
@pytest.mark.parametrize("role", ROLES_TO_TEST)
def test_role_actions(role):
    print(f'\n\n\nstart role:{role}\n')
    USERNAME = f"{NAMESPACE}_user_{gen_string()}"

    user = create_user(USERNAME, PASSWORD)
    create_group_with_user_and_role(user, role)

    expected_allows = ROLES_TO_TEST[role]

    # Test global actions
    for action in GLOBAL_ACTIONS:
        expect_pass = action in expected_allows
        action(user, PASSWORD, expect_pass)

    # Test object actions
    # for action in OBJECT_ACTIONS:
    #     expect_pass = action in expected_allows
    #     action(user, PASSWORD, expect_pass)
    print(f'\n\n\nend role:{role}\n')


@pytest.mark.role_rbac
def test_role_actions_for_admin():
    user = {'username': 'admin'}
    password = 'admin'
    for action in GLOBAL_ACTIONS:
        action(user, password, True)
    # for action in OBJECT_ACTIONS:
    #     action(user, password, True)
