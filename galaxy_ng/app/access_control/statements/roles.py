LOCKED_ROLES = {
    "galaxy.collection_admin": {
        "permissions": [
            "galaxy.add_namespace",
            "galaxy.change_namespace",
            "galaxy.delete_namespace",
            "galaxy.upload_to_namespace",
            "ansible.delete_collection",
            "ansible.change_collectionremote",
            "ansible.view_collectionremote",
            "ansible.modify_ansible_repo_content",
        ],
        "description": (
            "Create, delete and change collection namespaces. "
            "Upload and delete collections. Sync collections from remotes. "
            "Approve and reject collections.")
    },
    "galaxy.execution_environment_admin": {
        "permissions": [
            "container.delete_containerrepository",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
            "container.namespace_push_containerdistribution",
            "container.add_containernamespace",
            "container.change_containernamespace",
            "container.namespace_add_containerdistribution",
            "galaxy.add_containerregistryremote",
            "galaxy.change_containerregistryremote",
            "galaxy.delete_containerregistryremote",
        ],
        "description": (
            "Push, delete, and change execution environments. "
            "Create, delete and change remote registries.")
    },
    "galaxy.execution_environment_namespace_owner": {
        "permissions": [
            "container.change_containernamespace",
            "container.namespace_push_containerdistribution",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
            "container.namespace_add_containerdistribution",
        ],
        "description": (
            "Create and update execution environments under existing "
            "container namespaces.")
    },
    "galaxy.execution_environment_collaborator": {
        "permissions": [
            "container.namespace_push_containerdistribution",
            "container.namespace_change_containerdistribution",
            "container.namespace_modify_content_containerpushrepository",
        ],
        "description": "Change existing execution environments."
    },
    "galaxy.content_admin": {
        "permissions": [
            "ansible.modify_ansible_repo_content",
        ],
        "description": "Approve and reject collections."
    },
    "galaxy.namespace_owner": {
        "permissions": [
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
            "ansible.delete_collection",
        ],
        "description": "Change and upload collections to namespaces."
    },
    "galaxy.publisher": {
        "permissions": [
            "galaxy.upload_to_namespace",
            "ansible.delete_collection",
        ],
        "description": "Upload and delete collections."
    },
    "galaxy.group_admin": {
        "permissions": [
            "galaxy.view_group",
            "galaxy.delete_group",
            "galaxy.add_group",
            "galaxy.change_group",
        ],
        "description": "View, add, remove and change groups."
    },
    "galaxy.user_admin": {
        "permissions": [
            "galaxy.view_user",
            "galaxy.delete_user",
            "galaxy.add_user",
            "galaxy.change_user",
        ],
        "description": "View, add, remove and change users."
    },
    "galaxy.synclist_owner": {
        "permissions": [
            "galaxy.add_synclist",
            "galaxy.change_synclist",
            "galaxy.delete_synclist",
            "galaxy.view_synclist",
            "ansible.change_collectionremote",
        ],
        "description": "View, add, remove and change synclists."
    },
    "galaxy.task_admin": {
        "permissions": [
            "core.change_task",
            "core.delete_task",
            "core.view_task"
        ],
        "description": "View, and cancel any task."
    },
}
