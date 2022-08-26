import enum


class DeploymentMode(enum.Enum):
    STANDALONE = 'standalone'
    INSIGHTS = 'insights'


CURRENT_UI_API_VERSION = 'v1'
ALL_UI_API_VERSION = {'v1': 'v1/'}

COMMUNITY_DOMAINS = (
    'galaxy.ansible.com',
    'galaxy-dev.ansible.com',
    'galaxy-qa.ansible.com',
)

INBOUND_REPO_NAME_FORMAT = "inbound-{namespace_name}"

PERMISSIONS = {
    "galaxy.add_namespace": {
        # Short name to display in the UI
        "name": "Add namespace",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": None,

        # Description to use when the permission is being assigned globally
        "global_description": "Create a new namespace.",

        # Category to group the permission in the UI.
        "ui_category": "namespaces"
    },
    "galaxy.change_namespace": {
        "name": "Change namespace",

        "object_description": "Edit this namespace.",

        "global_description": "Edit any existing namespace.",

        "ui_category": "namespaces"
    },
    "galaxy.delete_namespace": {
        "name": "Delete namespace",

        "object_description": "Delete this namespace.",

        "global_description": "Delete any existing namespace.",

        "ui_category": "namespaces"
    },
    "galaxy.upload_to_namespace": {
        "name": "Upload to namespace",

        "object_description": "Upload collections to this namespace.",

        "global_description": "Upload collections to any existing namespace.",

        "ui_category": "namespaces"
    },
    "ansible.delete_collection": {
        "name": "Delete collection",

        "object_description": "Delete this collection.",

        "global_description": "Delete any existing collection.",

        "ui_category": "collections"
    },
    "ansible.modify_ansible_repo_content": {
        "name": "Modify Ansible repo content",

        "object_description": "Modify content of an Ansible repository.",

        "global_description": "Upload collections to any existing namespace.",

        "ui_category": "collection_namespace"
    },
    "galaxy.add_user": {
        "name": "Add user",

        "object_description": None,

        "global_description": "Add new users to the system.",

        "ui_category": "users"
    },
    "galaxy.change_user": {
        "name": "Change user",

        "object_description": "Edit this user.",

        "global_description": "Edit any existing user in the system.",

        "ui_category": "users"
    },
    "galaxy.delete_user": {
        "name": "Delete user",

        "object_description": "Delete this user.",

        "global_description": "Delete any existing user in the system.",

        "ui_category": "users"
    },
    "galaxy.view_user": {
        "name": "View user",

        "object_description": "View this user.",

        "global_description": "View any user in the system.",

        "ui_category": "users"
    },
    "galaxy.add_group": {
        "name": "Add group",

        "object_description": None,

        "global_description": "Create new groups to the system.",

        "ui_category": "groups"
    },
    "galaxy.change_group": {
        "name": "Change group",

        "object_description": "Edit this group",

        "global_description": "Edit any existing group in the system.",

        "ui_category": "groups"
    },
    "galaxy.delete_group": {
        "name": "Delete group",

        "object_description": "Delete this group.",

        "global_description": "Delete any group in the system.",

        "ui_category": "groups"
    },
    "galaxy.view_group": {
        "name": "View group",

        "object_description": "View this group.",

        "global_description": "View any existing group in the system.",

        "ui_category": "groups"
    },
    "container.change_containernamespace": {
        "name": "Change container namespace permissions",

        "object_description": "Edit permissions on this namespace.",

        "global_description": "Edit permissions on any existing namespace.",

        "ui_category": "containers"
    },
    "container.change_containernamespace": {
        "name": "Change container namespace permissions",

        "object_description": "Edit permissions on this namespace.",

        "global_description": "Edit permissions on any existing namespace.",

        "ui_category": "containers"
    },
    "container.namespace_change_containerdistribution": {
        "name": "Change containers",

        "object_description": "Edit this container.",

        "global_description": "Edit any container existing in the system.",

        "ui_category": "containers"
    },
    "container.add_containernamespace": {
        "name": "Create new containers",

        "object_description": None,

        "global_description": "Add new containers to the system.",

        "ui_category": "containers"
    },
    "container.delete_containerrepository": {
        "name": "Delete container repository",

        "object_description": "Delete this container repository.",

        "global_description": "Delete any existing container repository in the system.",

        "ui_category": "containers"
    },
    "container.namespace_push_containerdistribution": {
        "name": "Push to existing containers",

        "object_description": "Push to this namespace.",

        "global_description": "Push to any existing namespace in the system.",

        "ui_category": "containers"
    },
    "ansible.change_collectionremote": {
        "name": "Change collection remote",

        "object_description": "Edit this collection remote.",

        "global_description": "Edit any collection remote existing in the system.",

        "ui_category": "remotes"
    },
    "ansible.view_collectionremote": {
        "name": "View collection remote",

        "object_description": "View this collection remote.",

        "global_description": "View any collection remote existing in the system.",

        "ui_category": "remotes"
    },
    "galaxy.add_containerregistryremote": {
        "name": "Add remote registry",

        "object_description": None,

        "global_description": "Add remote registry to the system.",

        "ui_category": "registries"
    },
    "galaxy.change_containerregistryremote": {
        "name": "Change remote registry",

        "object_description": "Edit this remote registry.",

        "global_description": "Change any remote registry existing in the system.",

        "ui_category": "registries"
    },
    "galaxy.delete_containerregistryremote": {
        "name": "Delete remote registry",

        "object_description": "Delete this remote registry.",

        "global_description": "Delete any remote registry existing in the system.",

        "ui_category": "registries"
    },
    "core.change_task": {
        "name": "Change task",

        "object_description": "Edit this task.",

        "global_description": "Edit any task existing in the system.",

        "ui_category": "task_management"
    },
    "core.delete_task": {
        "name": "Delete task",

        "object_description": "Delete this task.",

        "global_description": "Delete any task existing in the system.",

        "ui_category": "task_management"
    },
    "core.view_task": {
        "name": "View all tasks",

        "object_description": "View this task.",

        "global_description": "View any task existing in the system.",

        "ui_category": "task_management"
    },
}
