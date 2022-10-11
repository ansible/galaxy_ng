from pulpcore.plugin.util import (
    assign_role,
    get_groups_with_perms_attached_roles,
    get_users_with_perms_attached_roles,
    remove_role
)

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.models.auth import Group, User


def add_username_to_groupname(username: str, groupname: str) -> None:
    user = User.objects.filter(username=username).first()
    group = Group.objects.filter(name=groupname).first()
    return add_user_to_group(user, group)


def add_user_to_group(user: User, group: Group) -> None:
    return group.user_set.add(user)


def remove_username_from_groupname(username: str, groupname: str) -> None:
    user = User.objects.filter(username=username).first()
    group = Group.objects.filter(name=groupname).first()
    return remove_user_from_group(user, group)


def remove_user_from_group(user: User, group: Group) -> None:
    return group.user_set.remove(user)


def add_groupname_to_v3_namespace_name(groupname: str, namespace_name: str) -> None:
    group = Group.objects.filter(name=groupname).first()
    namespace = Namespace.objects.filter(name=namespace_name).first()
    add_group_to_v3_namespace(group, namespace)


def add_group_to_v3_namespace(group: Group, namespace: Namespace) -> None:
    role_name = 'galaxy.collection_namespace_owner'
    current_groups = get_groups_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    if group in current_groups:
        return
    assign_role(role_name, group, namespace)


def remove_group_from_v3_namespace(group, namespace) -> None:
    role_name = 'galaxy.collection_namespace_owner'
    current_groups = get_groups_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    if group not in current_groups:
        return
    remove_role(role_name, group, namespace)


def add_user_to_v3_namespace(user: User, namespace: Namespace) -> None:
    role_name = 'galaxy.collection_namespace_owner'
    assign_role(role_name, user, namespace)


def get_v3_namespace_owners(namespace: Namespace) -> list:
    """
    Return a list of users that own a v3 namespace.
    """
    owners = list()
    current_groups = get_groups_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    for cgroup in current_groups:
        owners.extend(list(cgroup.user_set.all()))
    current_users = get_users_with_perms_attached_roles(
        namespace,
        include_model_permissions=False
    )
    owners.extend(list(current_users))
    owners = sorted(set(owners))
    return owners
