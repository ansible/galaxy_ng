"""Tests related to RBAC roles.

See: https://issues.redhat.com/browse/AAH-957
"""
import logging
from pickle import GLOBAL
import pytest

from .rbac_actions.utils import (
    NAMESPACE,
    create_group_with_user_and_role,
    create_user,
    gen_string,
)

from .rbac_actions.auth import (
    view_groups, delete_groups, add_groups, change_groups,
    view_users, delete_users, add_users, change_users,
    view_role, delete_role, add_role, change_role,
)
from .rbac_actions.misc import view_tasks, cancel_tasks
from .rbac_actions.collections import (
    create_collection_namespace,
    change_collection_namespace,
    delete_collection_namespace,
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
#     create_collection_namespace,
#     upload_collection_to_namespace,
#     deprecate_collection,
#     undeprecate_collection,
# ]
ROLES_TO_TEST = {
    "galaxy.content_admin": {
        create_collection_namespace,
        change_collection_namespace,
        delete_collection_namespace,
        view_groups,  # error?
        view_tasks,  # error?
        # upload_collection_to_namespace,
        # delete_collection,
        # configure_collection_sync,
        # launch_collection_sync,
        # view_sync_configuration,
        # approve_reject_collections,
        # deprecate_collection,
        # undeprecate_collection,
        #  ## insert EE actions here
    },
    # "galaxy.collection_admin": {
        # create_collection_namespace,
        # change_collection_namespace,
        # delete_collection_namespace,
        # upload_collection_to_namespace,
        # delete_collection,
        # configure_collection_sync,
        # launch_collection_sync,
        # view_sync_configuration,
        # approve_reject_collections,
        # deprecate_collection,
        # undeprecate_collection,
    # },
    # "galaxy.collection_publisher": {
        # upload_collection_to_namespace,
        # delete_collection,
        # deprecate_collection,
        # undeprecate_collection,
    # },
    # "galaxy.collection_curator": {
        # configure_collection_sync,
        # launch_collection_sync,
        # view_collection_sync,
        # approve_reject_collections,
    # },
    # "galaxy.collection_namespace_owner": {
        # create_collection_namespace,
        # upload_collection_to_namespace,
        # deprecate_collection,
        # undeprecate_collection,
    # },

    "galaxy.group_admin": {
        view_groups,
        delete_groups,
        add_groups,
        change_groups,
        view_tasks,  # error?
    },
    "galaxy.user_admin": {
        view_users,
        delete_users,
        add_users,
        change_users,
        view_groups,  # error?
        view_tasks,  # error?
    },
    "galaxy.task_admin": {
        view_tasks,
        # cancel_tasks,
        view_groups,  # error?
    }
}


@pytest.mark.role_rbac
@pytest.mark.parametrize("role", ROLES_TO_TEST)
def test_role_actions(role):
    print(f'\n\n\nstart role:{role}\n')
    PASSWORD = "p@ssword!"
    USERNAME = f"{NAMESPACE}_user_{gen_string()}"

    user = create_user(USERNAME, PASSWORD)
    create_group_with_user_and_role(user, role)

    expected_allows = ROLES_TO_TEST[role]

    # Test global actions
    for action in GLOBAL_ACTIONS:
        expect_pass = action in expected_allows
        action(user, PASSWORD, expect_pass)
        print(f'action:{action}')
        # print(f'action(user, PASSWORD, expected_pass):{action(user, PASSWORD, expect_pass)}')
        print(f'expected_allows:{expected_allows}')
        print(f'expect_pass:{expect_pass}')
        # was_action_allowed = action(user, PASSWORD, expect_pass)
        # if action in expected_allows:
        #     print(f'was_action_allowed:{was_action_allowed}')
        #     assert(was_action_allowed)
        # else:
        #     print(f'was_action_allowed:{was_action_allowed}')
        #     assert(not was_action_allowed)

    # Test object actions
    # for action in object_actions:
    #     was_action_allowed = action(role)
    #     if action in expected_allows:
    #         assert(was_action_allowed)
    #     else:
    #         assert(not was_action_allowed)
    print(f'\n\n\nend role:{role}\n')


# failures = []

# for action in GLOBAL_ACTIONS:
#     was_action_allowed = action(user, PASSWORD)
#     print(f'action:{action}')
#     print(f'action(user, PASSWORD):{action(user, PASSWORD)}')
#     if action in expected_allows and was_action_allowed:
#         print(f'was_action_allowed:{was_action_allowed}')
#         failures.append(action)
#     elif not was_action_allowed:
#         print(f'was_action_allowed:{was_action_allowed}')
#         failures.append(action)

# assert failures == []


# def test_role_actions_for_admin():
#     for action in GLOBAL_ACTIONS:
#         action('admin', 'admin', True)
#     # for action in OBJECT_ACTIONS:
#     #     action('admin', 'admin', True)
