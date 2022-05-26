"""Tests related to RBAC roles.

See: https://issues.redhat.com/browse/AAH-957
"""
import logging
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
]
# OBJECT_ACTIONS = []
ROLES_TO_TEST = {
    "galaxy.group_admin": {
        view_groups,
        delete_groups,
        add_groups,
        change_groups,
    },
    "galaxy.user_admin": {
        view_users,
        delete_users,
        add_users,
        change_users,
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
        was_action_allowed = action(user, PASSWORD)
        print(f'action:{action}')
        print(f'action(user, PASSWORD):{action(user, PASSWORD)}')
        if action in expected_allows:
            print(f'was_action_allowed:{was_action_allowed}')
            assert(was_action_allowed)
        else:
            print(f'was_action_allowed:{was_action_allowed}')
            assert(not was_action_allowed)

    # Test object actions
    # for action in object_actions:
    #     was_action_allowed = action(role)
    #     if action in expected_allows:
    #         assert(was_action_allowed)
    #     else:
    #         assert(not was_action_allowed)
    print(f'\n\n\nend role:{role}\n')
