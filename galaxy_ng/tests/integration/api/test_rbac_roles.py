"""Tests related to RBAC roles.

See: https://issues.redhat.com/browse/AAH-957
"""
import logging
import pytest
import requests

from .rbac_actions.utils import (
    ADMIN_CREDENTIALS,
    ADMIN_USER,
    ADMIN_PASSWORD,
    API_ROOT,
    NAMESPACE,
    PASSWORD,
    create_group_with_user_and_role,
    create_user,
    gen_string,
    del_user,
    del_group,
    ReusableCollection,
    ReusableContainerRegistry,
    # ReusableLocalContainer,  # waiting on pulp container fix
    ReusableRemoteContainer
)

from .rbac_actions.auth import (
    view_groups, delete_groups, add_groups, change_groups,
    view_users, delete_users, add_users, change_users,
    view_role, delete_role, add_role, change_role,
)
from .rbac_actions.misc import view_tasks
from .rbac_actions.collections import (
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
)
from .rbac_actions.exec_env import (
    # Remotes
    create_ee_remote,
    update_ee_remote,
    sync_remote_ee,

    # Registries
    delete_ee_registry,
    index_ee_registry,
    update_ee_registry,
    create_ee_registry,

    # Containers
    delete_ee,
    change_ee_description,
    change_ee_readme,
    change_ee_namespace,
    create_ee_local,
    create_ee_in_existing_namespace,
    push_updates_to_existing_ee,
    change_ee_tags,
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
    # Remotes
    create_ee_remote,
    update_ee_remote,
    sync_remote_ee,

    # Registries
    delete_ee_registry,
    index_ee_registry,
    update_ee_registry,
    create_ee_registry,

    # Containers
    delete_ee,
    change_ee_description,
    change_ee_readme,
    change_ee_namespace,
    create_ee_local,
    create_ee_in_existing_namespace,
    push_updates_to_existing_ee,
    change_ee_tags,

    # MISC
    view_tasks,
]
OBJECT_ACTIONS = [
    # change_collection_namespace_object,
    # upload_collection_to_namespace_object,
    # deprecate_collections_object,
    # undeprecate_collections_object,
    # change_exec_env_desc_object,
    # change_exec_env_readme_object,
    # create_containers_under_existing_container_namespace_object,
    # push_containers_to_existing_container_namespace_object,
    # change_container_namespace_object,
    # tag_untag_container_namespace_object,
    # sync_remote_container_object,
]

ROLES_TO_TEST = {
    "galaxy.content_admin": {
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
        # Remotes
        create_ee_remote,
        update_ee_remote,
        sync_remote_ee,

        # Registries
        delete_ee_registry,
        index_ee_registry,
        update_ee_registry,
        create_ee_registry,

        # Containers
        delete_ee,
        change_ee_description,
        change_ee_readme,
        change_ee_namespace,
        create_ee_local,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,
    },
    "galaxy.collection_admin": {
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,
        delete_collection,
        delete_collection_namespace,
        configure_collection_sync,
        launch_collection_sync,
        approve_collections,
        reject_collections,
        deprecate_collections,
        undeprecate_collections,
    },
    "galaxy.collection_publisher": {
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,
        deprecate_collections,
        undeprecate_collections,
    },
    "galaxy.collection_curator": {
        configure_collection_sync,
        launch_collection_sync,
        approve_collections,
        reject_collections,
    },
    # Object tests are incomplete
    # "galaxy.collection_namespace_owner": {
    #     view_groups,
    #     view_sync_configuration,
    #     view_tasks,
    #     change_collection_namespace_object,
    #     # upload_collection_to_namespace_object,
    #     # deprecate_collections_object,
    #     # undeprecate_collections_object,
    # },
    "galaxy.execution_environment_admin": {
        # EEs
        # Remotes
        create_ee_remote,
        update_ee_remote,
        sync_remote_ee,

        # Registries
        delete_ee_registry,
        index_ee_registry,
        update_ee_registry,
        create_ee_registry,

        # Containers
        delete_ee,
        change_ee_description,
        change_ee_readme,
        change_ee_namespace,
        create_ee_local,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,
    },
    "galaxy.execution_environment_publisher": {
        create_ee_remote,
        update_ee_remote,
        sync_remote_ee,
        change_ee_description,
        change_ee_readme,
        change_ee_namespace,
        create_ee_local,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,
    },
    # Object tests are incomplete
    # "galaxy.execution_environment_namespace_owner": {
    #     view_groups,
    #     view_sync_configuration,
    #     view_tasks,
    #     # change_exec_env_desc_object,
    #     # change_exec_env_readme_object,
    #     # create_containers_under_existing_container_namespace_object,
    #     # push_containers_to_existing_container_namespace_object,
    #     # change_container_namespace_object,
    #     # tag_untag_container_namespace_object,
    #     # sync_remote_container_object,
    # },
    # Object tests are incomplete
    # "galaxy.execution_environment_collaborator": {
    #     view_groups,
    #     view_sync_configuration,
    #     view_tasks,
    #     # change_exec_env_desc_object,
    #     # change_exec_env_readme_object,
    #     # push_containers_to_existing_container_namespace_object,
    #     # tag_untag_container_namespace_object,
    #     # sync_remote_container_object,
    # },
    "galaxy.group_admin": {
        add_groups,
        change_groups,
        delete_groups,
        view_role,
    },
    "galaxy.user_admin": {
        add_users,
        view_users,
        change_users,
        delete_users,
    },
    "galaxy.task_admin": {}
}


ACTIONS_FOR_ALL_USERS = {
    view_sync_configuration,
    view_groups,
    view_tasks,
    view_role,
}


@pytest.mark.role_rbac
@pytest.mark.standalone_only
@pytest.mark.parametrize("role", ROLES_TO_TEST)
def test_global_role_actions(role):
    registry = ReusableContainerRegistry(gen_string())
    registry_pk = registry.get_registry()["pk"]

    extra = {
        "collection": ReusableCollection(gen_string()),
        "registry": registry,
        "remote_ee": ReusableRemoteContainer(gen_string(), registry_pk)
    }

    USERNAME = f"{NAMESPACE}_user_{gen_string()}"

    user = create_user(USERNAME, PASSWORD)
    group = create_group_with_user_and_role(user, role)
    group_id = group['id']

    expected_allows = ROLES_TO_TEST[role]

    failures = []
    # Test global actions
    for action in GLOBAL_ACTIONS:
        expect_pass = action in expected_allows or action in ACTIONS_FOR_ALL_USERS
        try:
            action(user, PASSWORD, expect_pass, extra)
        except AssertionError:
            failures.append(action.__name__)

    # cleanup user, group
    requests.delete(f"{API_ROOT}_ui/v1/users/{user['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/groups/{group_id}/", auth=ADMIN_CREDENTIALS)

    del_user(user['id'])
    del_group(group_id)

    extra['collection'].cleanup()
    extra['registry'].cleanup()
    extra['remote_ee'].cleanup()

    assert failures == []


@pytest.mark.role_rbac
@pytest.mark.standalone_only
def test_role_actions_for_admin():
    registry = ReusableContainerRegistry(gen_string())
    registry_pk = registry.get_registry()["pk"]

    extra = {
        "collection": ReusableCollection(gen_string()),
        "registry": registry,
        "remote_ee": ReusableRemoteContainer(gen_string(), registry_pk)
    }
    failures = []

    # Test global actions
    for action in GLOBAL_ACTIONS:
        try:
            action({'username': ADMIN_USER}, ADMIN_PASSWORD, True, extra)
        except AssertionError:
            failures.append(action.__name__)

    extra['collection'].cleanup()
    extra['registry'].cleanup()
    extra['remote_ee'].cleanup()

    assert failures == []
