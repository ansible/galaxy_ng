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
        # Short name to display in the UI
        "name": "Change namespace",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this namespace.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit any existing namespace.",

        # Category to group the permission in the UI.
        "ui_category": "namespaces"
    },
      "galaxy.delete_namespace": {
        # Short name to display in the UI
        "name": "Delete namespace",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this namespace.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any existing namespace.",

        # Category to group the permission in the UI.
        "ui_category": "namespaces"
    },
      "galaxy.upload_to_namespace": {
        # Short name to display in the UI
        "name": "Upload to namespace",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Upload collections to this namespace.",

        # Description to use when the permission is being assigned globally
        "global_description": "Upload collections to any existing namespace.",

        # Category to group the permission in the UI.
        "ui_category": "namespaces"
    },
      "ansible.delete_collection": {
        # Short name to display in the UI
        "name": "Delete collection",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this collection.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any existing collection.",

        # Category to group the permission in the UI.
        "ui_category": "collections"
    },
      "ansible.modify_ansible_repo_content": {
        # Short name to display in the UI
        "name": "Modify Ansible repo content",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Modify content of an Ansible repository.",

        # Description to use when the permission is being assigned globally
        "global_description": "Upload collections to any existing namespace.",

        # Category to group the permission in the UI.
        "ui_category": "collection_namespace"
    },
       "galaxy.add_user": {
        # Short name to display in the UI
        "name": "Add user",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": None,

        # Description to use when the permission is being assigned globally
        "global_description": "Add new users to the system.",

        # Category to group the permission in the UI.
        "ui_category": "users"
    },
       "galaxy.change_user": {
        # Short name to display in the UI
        "name": "Change user",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this user.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit any existing user in the system.",

        # Category to group the permission in the UI.
        "ui_category": "users"
    },
       "galaxy.delete_user": {
        # Short name to display in the UI
        "name": "Delete user",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this user.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any existing user in the system.",

        # Category to group the permission in the UI.
        "ui_category": "users"
    },
       "galaxy.view_user": {
        # Short name to display in the UI
        "name": "View user",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "View this user.",

        # Description to use when the permission is being assigned globally
        "global_description": "View any user in the system.",

        # Category to group the permission in the UI.
        "ui_category": "users"
    },
        "galaxy.add_group": {
        # Short name to display in the UI
        "name": "Add group",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": None,

        # Description to use when the permission is being assigned globally
        "global_description": "Create new groups to the system.",

        # Category to group the permission in the UI.
        "ui_category": "groups"
    },
        "galaxy.change_group": {
        # Short name to display in the UI
        "name": "Change group",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this group",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit any existing group in the system.",

        # Category to group the permission in the UI.
        "ui_category": "groups"
    },
      "galaxy.delete_group": {
        # Short name to display in the UI
        "name": "Delete group",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this group.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any group in the system.",

        # Category to group the permission in the UI.
        "ui_category": "groups"
    },
        "galaxy.view_group": {
        # Short name to display in the UI
        "name": "View group",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "View this group.",

        # Description to use when the permission is being assigned globally
        "global_description": "View any existing group in the system.",

        # Category to group the permission in the UI.
        "ui_category": "groups"
    },
        "container.change_containernamespace": {
        # Short name to display in the UI
        "name": "Change container namespace permissions",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit permissions on this namespace.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit permissions on any existing namespace.",

        # Category to group the permission in the UI.
        "ui_category": "containers"
    },
       "container.change_containernamespace": {
        # Short name to display in the UI
        "name": "Change container namespace permissions",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit permissions on this namespace.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit permissions on any existing namespace.",

        # Category to group the permission in the UI.
        "ui_category": "containers"
    },
       "container.namespace_change_containerdistribution": {
        # Short name to display in the UI
        "name": "Change containers",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this container.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit any container existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "containers"
    },
       "container.add_containernamespace": {
        # Short name to display in the UI
        "name": "Create new containers",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": None,

        # Description to use when the permission is being assigned globally
        "global_description": "Add new containers to the system.",

        # Category to group the permission in the UI.
        "ui_category": "containers"
    },
       "container.delete_containerrepository": {
        # Short name to display in the UI
        "name": "Delete container repository",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this container repository.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any existing container repository in the system.",

        # Category to group the permission in the UI.
        "ui_category": "containers"
    },
       "container.namespace_push_containerdistribution": {
        # Short name to display in the UI
        "name": "Push to existing containers",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Push to this namespace.",

        # Description to use when the permission is being assigned globally
        "global_description": "Push to any existing namespace in the system.",

        # Category to group the permission in the UI.
        "ui_category": "containers"
    },
        "ansible.change_collectionremote": {
        # Short name to display in the UI
        "name": "Change collection remote",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this collection remote.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit any collection remote existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "remotes"
    },
        "ansible.view_collectionremote": {
        # Short name to display in the UI
        "name": "View collection remote",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "View this collection remote.",

        # Description to use when the permission is being assigned globally
        "global_description": "View any collection remote existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "remotes"
    },
        "galaxy.add_containerregistryremote": {
        # Short name to display in the UI
        "name": "Add remote registry",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": None,

        # Description to use when the permission is being assigned globally
        "global_description": "Add remote registry to the system.",

        # Category to group the permission in the UI.
        "ui_category": "registries"
    },
        "galaxy.change_containerregistryremote": {
        # Short name to display in the UI
        "name": "Change remote registry",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this remote registry.",

        # Description to use when the permission is being assigned globally
        "global_description": "Change any remote registry existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "registries"
    },
        "galaxy.delete_containerregistryremote": {
        # Short name to display in the UI
        "name": "Delete remote registry",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this remote registry.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any remote registry existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "registries"
    },
        "core.change_task": {
        # Short name to display in the UI
        "name": "Change task",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Edit this task.",

        # Description to use when the permission is being assigned globally
        "global_description": "Edit any task existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "task_management"
    },
        "core.delete_task": {
        # Short name to display in the UI
        "name": "Delete task",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "Delete this task.",

        # Description to use when the permission is being assigned globally
        "global_description": "Delete any task existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "task_management"
    },
        "core.view_task": {
        # Short name to display in the UI
        "name": "View all tasks",

        # Description to use when the permission is being assigned to a specifc object
        "object_description": "View this task.",

        # Description to use when the permission is being assigned globally
        "global_description": "View any task existing in the system.",

        # Category to group the permission in the UI.
        "ui_category": "task_management"
    },
}
