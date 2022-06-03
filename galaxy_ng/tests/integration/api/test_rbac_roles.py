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
    change_collection_namespace,
    delete_collection_namespace,
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
        #  ## insert EE actions here
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
        create_collection_namespace,
        change_collection_namespace,
        # upload_collection_to_namespace,
    },
    "galaxy.collection_curator": {
        create_collection_namespace,  # error?
        view_groups,  # error?
        view_tasks,  # error?
        configure_collection_sync,
        launch_collection_sync,
        # view_collection_sync,
        # approve_reject_collections,
    },
    "galaxy.collection_namespace_owner": {
        create_collection_namespace,  # error?
        view_groups,  # error?
        view_tasks,  # error?
        change_collection_namespace,
        # upload_collection_to_namespace,
    },
    "galaxy.group_admin": {
        create_collection_namespace,  # error?
        view_tasks,  # error?
        view_groups,
        delete_groups,
        add_groups,
        change_groups,
    },
    "galaxy.user_admin": {
        create_collection_namespace,  # error?
        view_groups,  # error?
        view_tasks,  # error?
        view_users,
        delete_users,
        add_users,
        change_users,
    },
    "galaxy.task_admin": {
        create_collection_namespace,  # error?
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
    #     print(f'action:{action}')
    #     print(f'expected_allows:{expected_allows}')
    #     print(f'expect_pass:{expect_pass}')

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
