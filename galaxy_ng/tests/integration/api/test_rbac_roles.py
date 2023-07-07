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
    create_group_for_user,
    create_user,
    gen_string,
    add_group_role,
    ReusableCollection,
    ReusableContainerRegistry,
    ReusableRemoteContainer,
    ReusableLocalContainer,
    ReusableAnsibleRepository
)

from .rbac_actions.auth import (
    view_groups,
    delete_groups,
    add_groups,
    change_groups,
    add_pulp_groups,
    delete_pulp_groups,
    view_pulp_groups,
    view_users,
    delete_users,
    add_users,
    change_users,
    view_role,
    delete_role,
    add_role,
    change_role,
)
from .rbac_actions.misc import view_tasks
from .rbac_actions.collections import (
    create_collection_namespace,
    change_collection_namespace,
    delete_collection_namespace,
    upload_collection_to_namespace,
    upload_collection_to_custom_staging_repo,
    upload_collection_to_custom_repo,
    delete_collection,
    configure_collection_sync,
    launch_collection_sync,
    view_sync_configuration,
    approve_collections,
    reject_collections,
    deprecate_collections,
    undeprecate_collections,
    upload_collection_to_other_pipeline_repo,
    copy_collection_version,
    copy_multiple_collection_version,
    move_collection_version,

    # ansible repository
    view_ansible_repository,
    add_ansible_repository,
    modify_ansible_repository,
    rebuild_metadata_ansible_repository,
    sign_ansible_repository,
    sync_ansible_repository,
    delete_ansible_repository,
    collection_repo_list_roles,
    collection_repo_add_role,
    collection_repo_remove_role,
    private_repo_list,
    private_distro_list,
    private_collection_version_list,
    view_private_repository_version,
    private_repo_v3,

    # ansible repository version
    view_ansible_repository_version,
    rebuild_metadata_ansible_repository_version,
    repair_ansible_repository_version,
    delete_ansible_repository_version,

    # ansible distribution
    view_ansible_distribution,
    add_ansible_distribution,
    change_ansible_distribution,
    delete_ansible_distribution,

    # ansible collection remote
    view_ansible_remote,
    add_ansible_remote,
    change_ansible_remote,
    delete_ansible_remote,
    collection_remote_list_roles,
    collection_remote_add_role,
    collection_remote_remove_role,
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
    create_ee_local,
    create_ee_in_existing_namespace,
    push_updates_to_existing_ee,
    change_ee_tags,

    # Container namespace
    ee_namespace_list_roles,
    ee_namespace_add_role,
    ee_namespace_remove_role
)
from ..utils.tools import generate_random_string

log = logging.getLogger(__name__)

# Order is important, CRU before D actions
GLOBAL_ACTIONS = {
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
    add_pulp_groups,
    delete_pulp_groups,
    view_pulp_groups,

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
    upload_collection_to_custom_staging_repo,
    upload_collection_to_custom_repo,
    upload_collection_to_other_pipeline_repo,
    private_repo_list,
    private_distro_list,
    private_collection_version_list,
    view_private_repository_version,
    private_repo_v3,
    copy_collection_version,
    copy_multiple_collection_version,
    move_collection_version,

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
    create_ee_local,
    create_ee_in_existing_namespace,
    push_updates_to_existing_ee,
    change_ee_tags,
    ee_namespace_list_roles,
    ee_namespace_add_role,
    ee_namespace_remove_role,

    # MISC
    view_tasks,

    # ansible repository
    view_ansible_repository,
    add_ansible_repository,
    modify_ansible_repository,
    rebuild_metadata_ansible_repository,
    sign_ansible_repository,
    sync_ansible_repository,
    delete_ansible_repository,
    collection_repo_list_roles,
    collection_repo_add_role,
    collection_repo_remove_role,

    # ansible repository version
    view_ansible_repository_version,
    rebuild_metadata_ansible_repository_version,
    repair_ansible_repository_version,
    delete_ansible_repository_version,

    # ansible distribution
    view_ansible_distribution,
    add_ansible_distribution,
    change_ansible_distribution,
    delete_ansible_distribution,

    # ansible collection remote
    view_ansible_remote,
    add_ansible_remote,
    change_ansible_remote,
    delete_ansible_remote,
    collection_remote_list_roles,
    collection_remote_add_role,
    collection_remote_remove_role,
}

# TODO: Update object tests to include delete actions
OBJECT_ACTIONS = {
    # ansible
    change_collection_namespace,
    upload_collection_to_namespace,
    deprecate_collections,
    undeprecate_collections,
    upload_collection_to_custom_repo,
    upload_collection_to_custom_staging_repo,
    collection_repo_list_roles,
    collection_repo_add_role,
    collection_repo_remove_role,
    private_repo_list,
    private_distro_list,
    private_collection_version_list,
    view_private_repository_version,
    private_repo_v3,

    # ee
    change_ee_description,
    change_ee_readme,
    create_ee_in_existing_namespace,
    push_updates_to_existing_ee,
    change_ee_tags,
    sync_remote_ee,
    ee_namespace_list_roles,
    ee_namespace_add_role,
    ee_namespace_remove_role
}

OBJECT_ROLES_TO_TEST = {
    # COLLECTIONS
    "galaxy.collection_namespace_owner": {
        change_collection_namespace,
        upload_collection_to_namespace,
        upload_collection_to_custom_staging_repo,
        deprecate_collections,
        undeprecate_collections,
    },
    "galaxy.collection_publisher": {
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,
        upload_collection_to_custom_staging_repo,
        deprecate_collections,
        undeprecate_collections,
    },
    "galaxy.ansible_repository_owner": {
        # ansible repository
        view_ansible_repository,
        add_ansible_repository,
        modify_ansible_repository,
        rebuild_metadata_ansible_repository,
        sign_ansible_repository,
        sync_ansible_repository,
        delete_ansible_repository,
        approve_collections,
        reject_collections,
        private_repo_list,
        private_distro_list,
        private_collection_version_list,
        view_private_repository_version,
        private_repo_v3,
        copy_collection_version,
        copy_multiple_collection_version,
        move_collection_version,

        # ansible repository version
        view_ansible_repository_version,
        rebuild_metadata_ansible_repository_version,
        repair_ansible_repository_version,
        delete_ansible_repository_version,
        collection_repo_list_roles,
        collection_repo_add_role,
        collection_repo_remove_role,

        # ansible distribution
        view_ansible_distribution,
        add_ansible_distribution,
        change_ansible_distribution,
        delete_ansible_distribution,
    },

    # EEs
    "galaxy.execution_environment_publisher": {
        create_ee_remote,
        update_ee_remote,
        sync_remote_ee,
        change_ee_description,
        change_ee_readme,
        create_ee_local,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,
        ee_namespace_list_roles,
        ee_namespace_add_role,
        ee_namespace_remove_role
    },
    "galaxy.execution_environment_namespace_owner": {
        update_ee_remote,
        change_ee_description,
        change_ee_readme,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,
        sync_remote_ee,
        ee_namespace_list_roles,
        ee_namespace_add_role,
        ee_namespace_remove_role
    },
    "galaxy.execution_environment_collaborator": {
        update_ee_remote,
        change_ee_description,
        change_ee_readme,
        push_updates_to_existing_ee,
        change_ee_tags,
        sync_remote_ee,
    },


}

ROLES_TO_TEST = {
    "galaxy.content_admin": {
        # COLLECTIONS
        create_collection_namespace,
        change_collection_namespace,
        delete_collection_namespace,
        upload_collection_to_namespace,
        upload_collection_to_custom_repo,
        upload_collection_to_custom_staging_repo,
        delete_collection,
        configure_collection_sync,
        launch_collection_sync,
        view_sync_configuration,
        approve_collections,
        reject_collections,
        deprecate_collections,
        undeprecate_collections,
        private_repo_list,
        private_distro_list,
        private_collection_version_list,
        view_private_repository_version,
        private_repo_v3,
        copy_collection_version,
        copy_multiple_collection_version,
        move_collection_version,

        # ansible repository
        view_ansible_repository,
        add_ansible_repository,
        modify_ansible_repository,
        rebuild_metadata_ansible_repository,
        sign_ansible_repository,
        sync_ansible_repository,
        delete_ansible_repository,
        collection_repo_list_roles,
        collection_repo_add_role,
        collection_repo_remove_role,

        # ansible repository version
        view_ansible_repository_version,
        rebuild_metadata_ansible_repository_version,
        repair_ansible_repository_version,
        delete_ansible_repository_version,

        # ansible distribution
        view_ansible_distribution,
        add_ansible_distribution,
        change_ansible_distribution,
        delete_ansible_distribution,

        # ansible collection remote
        view_ansible_remote,
        add_ansible_remote,
        change_ansible_remote,
        delete_ansible_remote,
        collection_remote_list_roles,
        collection_remote_add_role,
        collection_remote_remove_role,

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
        create_ee_local,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,

        # Container namespace
        ee_namespace_list_roles,
        ee_namespace_add_role,
        ee_namespace_remove_role

    },
    "galaxy.collection_admin": {
        create_collection_namespace,
        change_collection_namespace,
        upload_collection_to_namespace,
        upload_collection_to_custom_repo,
        upload_collection_to_custom_staging_repo,
        delete_collection,
        delete_collection_namespace,
        configure_collection_sync,
        launch_collection_sync,
        approve_collections,
        reject_collections,
        deprecate_collections,
        undeprecate_collections,
        private_repo_list,
        private_distro_list,
        private_collection_version_list,
        view_private_repository_version,
        private_repo_v3,
        copy_collection_version,
        copy_multiple_collection_version,
        move_collection_version,

        # ansible repository
        view_ansible_repository,
        add_ansible_repository,
        modify_ansible_repository,
        rebuild_metadata_ansible_repository,
        sign_ansible_repository,
        sync_ansible_repository,
        delete_ansible_repository,
        collection_repo_list_roles,
        collection_repo_add_role,
        collection_repo_remove_role,

        # ansible repository version
        view_ansible_repository_version,
        rebuild_metadata_ansible_repository_version,
        repair_ansible_repository_version,
        delete_ansible_repository_version,

        # ansible distribution
        view_ansible_distribution,
        add_ansible_distribution,
        change_ansible_distribution,
        delete_ansible_distribution,

        # ansible collection remote
        view_ansible_remote,
        add_ansible_remote,
        change_ansible_remote,
        delete_ansible_remote,
        collection_remote_list_roles,
        collection_remote_add_role,
        collection_remote_remove_role,
    },
    "galaxy.collection_curator": {
        configure_collection_sync,
        launch_collection_sync,
        approve_collections,
        reject_collections,

        # ansible repository
        view_ansible_repository,
        add_ansible_repository,
        modify_ansible_repository,
        rebuild_metadata_ansible_repository,
        sign_ansible_repository,
        sync_ansible_repository,
        delete_ansible_repository,
        private_repo_list,
        private_distro_list,
        private_collection_version_list,
        view_private_repository_version,
        private_repo_v3,
        copy_collection_version,
        copy_multiple_collection_version,
        move_collection_version,

        # ansible repository version
        view_ansible_repository_version,
        rebuild_metadata_ansible_repository_version,
        repair_ansible_repository_version,
        delete_ansible_repository_version,
        collection_repo_list_roles,
        collection_repo_add_role,
        collection_repo_remove_role,

        # ansible distribution
        view_ansible_distribution,
        add_ansible_distribution,
        change_ansible_distribution,
        delete_ansible_distribution,

        # ansible collection remote
        view_ansible_remote,
        add_ansible_remote,
        change_ansible_remote,
        delete_ansible_remote,
        collection_remote_list_roles,
        collection_remote_add_role,
        collection_remote_remove_role,
    },
    "galaxy.collection_remote_owner": {
        configure_collection_sync,
        launch_collection_sync,
        view_ansible_remote,
        add_ansible_remote,
        change_ansible_remote,
        delete_ansible_remote,
        collection_remote_list_roles,
        collection_remote_add_role,
        collection_remote_remove_role,
    },
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
        create_ee_local,
        create_ee_in_existing_namespace,
        push_updates_to_existing_ee,
        change_ee_tags,

        # Container namespace
        ee_namespace_list_roles,
        ee_namespace_add_role,
        ee_namespace_remove_role

    },
    "galaxy.group_admin": {
        add_groups,
        change_groups,
        delete_groups,
        view_role,
        add_pulp_groups,
        delete_pulp_groups,
        view_pulp_groups,
    },
    "galaxy.user_admin": {
        add_users,
        view_users,
        change_users,
        delete_users,
    },
    "galaxy.task_admin": {}
}
ROLES_TO_TEST.update(OBJECT_ROLES_TO_TEST)

ACTIONS_FOR_ALL_USERS = {
    view_ansible_distribution,
    view_ansible_repository,
    view_ansible_repository_version,
    view_sync_configuration,
    view_groups,
    view_tasks,
    view_role,
    view_pulp_groups,
}

DENIED_FOR_ALL_USERS = {
    upload_collection_to_other_pipeline_repo,
}


REUSABLE_EXTRA = {}


# initialize the extra objects once for all the tests. This saves ~20 seconds per test
def _get_reusable_extras():
    global REUSABLE_EXTRA

    if len(REUSABLE_EXTRA) == 0:
        _registry = ReusableContainerRegistry(gen_string())
        _registry_pk = _registry.get_registry()["id"]

        REUSABLE_EXTRA = {
            "collection": ReusableCollection(gen_string()),
            "registry": _registry,
            "remote_ee": ReusableRemoteContainer(gen_string(), _registry_pk),
            "local_ee": ReusableLocalContainer(gen_string()),
            "custom_staging_repo": ReusableAnsibleRepository(
                f"repo-test-{generate_random_string()}", is_staging=True),
            "custom_repo": ReusableAnsibleRepository(
                f"repo-test-{generate_random_string()}", is_staging=False),
            "private_repo": ReusableAnsibleRepository(
                f"repo-test-{generate_random_string()}", is_staging=False, is_private=True,
                add_collection=True),
        }

    return REUSABLE_EXTRA


@pytest.mark.rbac_roles
@pytest.mark.parametrize("role", ROLES_TO_TEST)
def test_global_role_actions(role):
    USERNAME = f"{NAMESPACE}_user_{gen_string()}"

    user = create_user(USERNAME, PASSWORD)
    group = create_group_for_user(user, role)
    group_id = group['id']

    expected_allows = ROLES_TO_TEST[role]

    extra = _get_reusable_extras()

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

    assert failures == []


@pytest.mark.rbac_roles
@pytest.mark.parametrize("role", OBJECT_ROLES_TO_TEST)
def test_object_role_actions(role):
    USERNAME = f"{NAMESPACE}_user_{gen_string()}"

    extra = _get_reusable_extras()

    namespace_href = extra["collection"].get_namespace()["pulp_href"]
    repo_href = extra["custom_repo"].get_repo()["pulp_href"]
    private_repo_href = extra["private_repo"].get_repo()["pulp_href"]
    local_ee_href = extra["local_ee"].get_namespace()["pulp_href"]
    remote_ee_href = extra["remote_ee"].get_namespace()["pulp_href"]

    user = create_user(USERNAME, PASSWORD)
    # create group without any global roles
    group = create_group_for_user(user)
    group_id = group['id']

    def _apply_roles():
        # assign object roles
        if "collection" in role:
            add_group_role(group["pulp_href"], role, namespace_href)

        if "execution_environment" in role:
            add_group_role(group["pulp_href"], role, local_ee_href)
            add_group_role(group["pulp_href"], role, remote_ee_href)

        # for the repo owner role, grant them collection namespace permissions
        # too so that they can upload collections to their repository.
        if role == "galaxy.ansible_repository_owner":
            add_group_role(group["pulp_href"], "galaxy.collection_namespace_owner", namespace_href)
            add_group_role(group["pulp_href"], role, repo_href)
            add_group_role(group["pulp_href"], role, private_repo_href)

    failures = []
    expected_allows = OBJECT_ROLES_TO_TEST[role]

    # since we're also applying the namespace owner role to test if the user can
    # upload to repositories they own (when they have namespace perms), we also
    # need to add the namespace owner actions to the list of expected allows
    if role == "galaxy.ansible_repository_owner":
        expected_allows = expected_allows.union({upload_collection_to_custom_repo})
        expected_allows = expected_allows.union(
            OBJECT_ROLES_TO_TEST["galaxy.collection_namespace_owner"])

    # Test global actions
    for action in OBJECT_ACTIONS:
        # re apply roles in case they get reset
        _apply_roles()
        expect_pass = action in expected_allows or action in ACTIONS_FOR_ALL_USERS
        try:
            action(user, PASSWORD, expect_pass, extra)
        except AssertionError:
            failures.append(action.__name__)

    # cleanup user, group
    requests.delete(f"{API_ROOT}_ui/v1/users/{user['id']}/", auth=ADMIN_CREDENTIALS)
    requests.delete(f"{API_ROOT}_ui/v1/groups/{group_id}/", auth=ADMIN_CREDENTIALS)

    assert failures == []


@pytest.mark.rbac_roles
def test_role_actions_for_admin():
    extra = _get_reusable_extras()
    failures = []

    # Test global actions
    for action in GLOBAL_ACTIONS:
        expect_pass = action not in DENIED_FOR_ALL_USERS
        try:
            action({'username': ADMIN_USER}, ADMIN_PASSWORD, expect_pass, extra)
        except AssertionError:
            failures.append(action.__name__)

    assert failures == []


@pytest.mark.rbac_roles
def test_all_actions_are_tested():
    """
    Ensures that all of the actions defined in ROLES_TO_TEST and OBJECT_ROLES_TO_TEST
    are also included in GLOBAL_ACTIONS
    """

    tested_actions = {action.__name__ for action in GLOBAL_ACTIONS}
    role_actions = set()

    for role in ROLES_TO_TEST:
        role_actions = role_actions.union([action.__name__ for action in ROLES_TO_TEST[role]])

    for role in OBJECT_ROLES_TO_TEST:
        role_actions = role_actions.union(
            [action.__name__ for action in OBJECT_ROLES_TO_TEST[role]])

    # assert that all of the actions declared on the roles are also declared
    # in the global set of tests
    diff = role_actions.difference(tested_actions)
    assert diff == set()
