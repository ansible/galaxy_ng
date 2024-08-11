_LOCKED_ROLES = {
    # Manage all content types.
    "galaxy.content_admin": {
        "permissions": {},
        "inherit_from": ["galaxy.collection_admin", "galaxy.execution_environment_admin"],
    },

    # COLLECTIONS

    # Create, delete and change collection namespaces.
    # Upload and delete collections. Sync collections from remotes.
    # Approve and reject collections.
    "galaxy.collection_admin": {
        "permissions": {
            "ansible.delete_collection",
            "ansible.repair_ansiblerepository",
            "galaxy.delete_namespace",
        },
        "inherit_from": ["galaxy.collection_publisher", "galaxy.collection_curator"],
    },
    # Upload and modify collections.
    "galaxy.collection_publisher": {
        "permissions": {
            "galaxy.add_namespace",
        },
        "inherit_from": ["galaxy.collection_namespace_owner"],
    },
    # Approve, reject and sync collections from remotes.
    "galaxy.collection_curator": {
        "permissions": {},
        "inherit_from": ["galaxy.ansible_repository_owner", "galaxy.collection_remote_owner"],
    },
    # Create and managing collection remotes
    "galaxy.collection_remote_owner": {
        "permissions": {
            "ansible.view_collectionremote",
            "ansible.add_collectionremote",
            "ansible.change_collectionremote",
            "ansible.delete_collectionremote",
            "ansible.manage_roles_collectionremote",
        },
        "inherit_from": []
    },
    # Manager ansible collection repositories
    "galaxy.ansible_repository_owner": {
        "permissions": {
            "ansible.modify_ansible_repo_content",
            "ansible.view_ansiblerepository",
            "ansible.add_ansiblerepository",
            "ansible.change_ansiblerepository",
            "ansible.delete_ansiblerepository",
            "ansible.repair_ansiblerepository",
            "ansible.sign_ansiblerepository",
            "ansible.manage_roles_ansiblerepository",
        },
        "inherit_from": [],
    },
    # Change and upload collections to namespaces.
    "galaxy.collection_namespace_owner": {
        "permissions": {
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
        },
        "inherit_from": [],
    },

    # EXECUTION ENVIRONMENTS

    # Push, delete and change execution environments.
    # Create, delete and change remote registries.
    "galaxy.execution_environment_admin": {
        "permissions": {
            "container.delete_containerrepository",
            "galaxy.add_containerregistryremote",
            "galaxy.change_containerregistryremote",
            "galaxy.delete_containerregistryremote",
            "container.manage_roles_containernamespace"
        },
        "inherit_from": ["galaxy.execution_environment_publisher"],
    },
    # Push and change execution environments.
    "galaxy.execution_environment_publisher": {
        "permissions": {
            "container.add_containernamespace",
        },
        "inherit_from": ["galaxy.execution_environment_namespace_owner"],
    },
    # Create and update execution environments under existing container namespaces.
    "galaxy.execution_environment_namespace_owner": {
        "permissions": {
            "container.change_containernamespace",
            "container.namespace_add_containerdistribution",
            "container.manage_roles_containernamespace",
            "container.view_containernamespace"
        },
        "inherit_from": ["galaxy.execution_environment_collaborator"],
    },
    # Change existing execution environments.
    "galaxy.execution_environment_collaborator": {
        "permissions": {
            "container.namespace_push_containerdistribution",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
        },
        "inherit_from": [],
    },

    # ADMIN STUFF

    # View, add, remove and change groups.
    "galaxy.group_admin": {
        "permissions": {
            "galaxy.view_group",
            "galaxy.delete_group",
            "galaxy.add_group",
            "galaxy.change_group",
        },
        "inherit_from": [],
    },
    # View, add, remove and change users.
    "galaxy.user_admin": {
        "permissions": {
            "galaxy.view_user",
            "galaxy.delete_user",
            "galaxy.add_user",
            "galaxy.change_user",
        },
        "inherit_from": [],
    },
    # View, add, remove and change synclists.
    "galaxy.synclist_owner": {
        "permissions": {
            "galaxy.add_synclist",
            "galaxy.change_synclist",
            "galaxy.delete_synclist",
            "galaxy.view_synclist",
        },
        "inherit_from": [],
    },
    # View and cancel any task.
    "galaxy.task_admin": {
        "permissions": {
            "core.change_task",
            "core.delete_task",
            "core.view_task"
        },
        "inherit_from": [],
    },
    # View and cancel any task.
    "galaxy.auditor": {
        "permissions": {
            "ansible.view_ansiblerepository",
            "ansible.view_collectionremote",
            "core.view_task",
            "galaxy.view_group",
            "galaxy.view_user",
        },
        "inherit_from": [],
    },
}


def _process_permissions(role, roles):
    if roles[role]["inherit_from"] == []:
        return roles[role]["permissions"]
    else:
        permissions = set()
        for child in roles[role]["inherit_from"]:
            permissions = permissions.union(_process_permissions(child, roles))
        return permissions.union(roles[role]["permissions"])


def _process_locked_roles(roles):
    locked = dict()
    for role in roles:
        locked[role] = {"permissions": list(_process_permissions(role, roles))}
    return locked


LOCKED_ROLES = _process_locked_roles(_LOCKED_ROLES)
