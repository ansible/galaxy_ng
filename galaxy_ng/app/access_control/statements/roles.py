_LOCKED_ROLES = {
    "galaxy.content_admin": {
        "description": "Manage all content types.",
        "permissions": {},
        "inherit_from": ["galaxy.collection_admin", "galaxy.execution_environment_admin"],
    },

    # COLLECTIONS

    "galaxy.collection_admin": {
        "description": (
            "Create, delete and change collection namespaces. "
            "Upload and delete collections. Sync collections from remotes. "
            "Approve and reject collections."
        ),
        "permissions": {
            "ansible.delete_collection",
            "ansible.repair_ansiblerepository",
            "galaxy.delete_namespace",
        },
        "inherit_from": ["galaxy.collection_publisher", "galaxy.collection_curator"],
    },
    "galaxy.collection_publisher": {
        "description": "Upload and modify collections.",
        "permissions": {
            "galaxy.add_namespace",
        },
        "inherit_from": ["galaxy.collection_namespace_owner"],
    },
    "galaxy.collection_curator": {
        "description": "Approve, reject and sync collections from remotes.",
        "permissions": {},
        "inherit_from": ["galaxy.ansible_repository_owner", "galaxy.collection_remote_owner"],
    },
    "galaxy.collection_remote_owner": {
        "description": "Create and manage collection remotes.",
        "permissions": {
            "ansible.view_collectionremote",
            "ansible.add_collectionremote",
            "ansible.change_collectionremote",
            "ansible.delete_collectionremote",
            "ansible.manage_roles_collectionremote",
        },
        "inherit_from": []
    },
    "galaxy.ansible_repository_owner": {
        "description": "Manage ansible collection repositories.",
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
    "galaxy.collection_namespace_owner": {
        "description": "Change and upload collections to namespaces.",
        "permissions": {
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
        },
        "inherit_from": [],
    },

    # EXECUTION ENVIRONMENTS

    "galaxy.execution_environment_admin": {
        "description": (
            "Push, delete and change execution environments. "
            "Create, delete and change remote registries."
        ),
        "permissions": {
            "container.delete_containerrepository",
            "galaxy.add_containerregistryremote",
            "galaxy.change_containerregistryremote",
            "galaxy.delete_containerregistryremote",
            "container.manage_roles_containernamespace"
        },
        "inherit_from": ["galaxy.execution_environment_publisher"],
    },
    "galaxy.execution_environment_publisher": {
        "description": "Push and change execution environments.",
        "permissions": {
            "container.add_containernamespace",
        },
        "inherit_from": ["galaxy.execution_environment_namespace_owner"],
    },
    "galaxy.execution_environment_namespace_owner": {
        "description": (
            "Create and update execution environments under existing container namespaces."
        ),
        "permissions": {
            "container.change_containernamespace",
            "container.namespace_add_containerdistribution",
            "container.manage_roles_containernamespace",
            "container.view_containernamespace"
        },
        "inherit_from": ["galaxy.execution_environment_collaborator"],
    },
    "galaxy.execution_environment_collaborator": {
        "description": "Change existing execution environments.",
        "permissions": {
            "container.namespace_push_containerdistribution",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
        },
        "inherit_from": [],
    },

    # ADMIN STUFF

    "galaxy.group_admin": {
        "description": "View, add, remove and change groups.",
        "permissions": {
            "galaxy.view_group",
            "galaxy.delete_group",
            "galaxy.add_group",
            "galaxy.change_group",
        },
        "inherit_from": [],
    },
    "galaxy.user_admin": {
        "description": "View, add, remove and change users.",
        "permissions": {
            "galaxy.view_user",
            "galaxy.delete_user",
            "galaxy.add_user",
            "galaxy.change_user",
        },
        "inherit_from": [],
    },
    "galaxy.synclist_owner": {
        "description": "View, add, remove and change synclists.",
        "permissions": {
            "galaxy.add_synclist",
            "galaxy.change_synclist",
            "galaxy.delete_synclist",
            "galaxy.view_synclist",
        },
        "inherit_from": [],
    },
    "galaxy.task_admin": {
        "description": "View and cancel any task.",
        "permissions": {
            "core.change_task",
            "core.delete_task",
            "core.view_task"
        },
        "inherit_from": [],
    },
    "galaxy.auditor": {
        "description": (
            "View repositories, remotes, tasks, groups, and users for auditing purposes."
        ),
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
    locked = {}
    for role in roles:
        locked[role] = {"permissions": list(_process_permissions(role, roles))}
    return locked


LOCKED_ROLES = _process_locked_roles(_LOCKED_ROLES)
