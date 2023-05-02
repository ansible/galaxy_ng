import enum
from django.utils.translation import gettext_lazy as _


class DeploymentMode(enum.Enum):
    STANDALONE = 'standalone'
    INSIGHTS = 'insights'


CURRENT_UI_API_VERSION = 'v1'
ALL_UI_API_VERSION = {'v1': 'v1/'}

COMMUNITY_DOMAINS = (
    'galaxy.ansible.com',
    'galaxy-dev.ansible.com',
    'galaxy-qa.ansible.com',
    'beta-galaxy.ansible.com',
)

INBOUND_REPO_NAME_FORMAT = "inbound-{namespace_name}"

PERMISSIONS = {
    "galaxy.add_namespace": {
        # Short name to display in the UI
        "name": _("Add namespace"),
        # Description to use when the permission is being assigned to a specifc object
        "object_description": None,
        # Description to use when the permission is being assigned globally
        "global_description": _("Create a new namespace."),
        # Category to group the permission in the UI.
        "ui_category": _("Collection Namespaces"),
    },
    "galaxy.change_namespace": {
        "name": _("Change namespace"),
        "object_description": _("Edit this namespace."),
        "global_description": _("Edit any existing namespace."),
        "ui_category": _("Collection Namespaces"),
    },
    "galaxy.delete_namespace": {
        "name": _("Delete namespace"),
        "object_description": _("Delete this namespace."),
        "global_description": _("Delete any existing namespace."),
        "ui_category": _("Collection Namespaces"),
    },
    "galaxy.upload_to_namespace": {
        "name": _("Upload to namespace"),
        "object_description": _("Upload collections to this namespace."),
        "global_description": _("Upload collections to any existing namespace."),
        "ui_category": _("Collection Namespaces"),
    },
    "ansible.delete_collection": {
        "name": _("Delete collection"),
        "object_description": _("Delete this collection."),
        "global_description": _("Delete any existing collection."),
        "ui_category": _("Collections"),
    },
    "ansible.modify_ansible_repo_content": {
        "name": _("Modify Ansible repo content"),
        "object_description": _("Modify content of this Ansible repository."),
        "global_description": _("Upload collections to any existing namespace."),
        "ui_category": _("Collections"),
    },
    "ansible.sign_ansiblerepository": {
        "name": _("Sign collections"),
        "object_description": _("Sign collections in this repository."),
        "global_description": _("Sign collections in any repository."),
        "ui_category": _("Collections"),
    },
    "galaxy.add_user": {
        "name": _("Add user"),
        "object_description": None,
        "global_description": _("Add new users to the system."),
        "ui_category": _("Users"),
    },
    "galaxy.change_user": {
        "name": _("Change user"),
        "object_description": _("Edit this user."),
        "global_description": _("Edit any existing user in the system."),
        "ui_category": _("Users"),
    },
    "galaxy.delete_user": {
        "name": _("Delete user"),
        "object_description": _("Delete this user."),
        "global_description": _("Delete any existing user in the system."),
        "ui_category": _("Users"),
    },
    "galaxy.view_user": {
        "name": _("View user"),
        "object_description": _("View this user."),
        "global_description": _("View any user in the system."),
        "ui_category": _("Users"),
    },
    "galaxy.add_group": {
        "name": _("Add group"),
        "object_description": None,
        "global_description": _("Create new groups in the system."),
        "ui_category": _("Groups"),
    },
    "galaxy.change_group": {
        "name": _("Change group"),
        "object_description": _("Edit this group"),
        "global_description": _("Edit any existing group in the system."),
        "ui_category": _("Groups"),
    },
    "galaxy.delete_group": {
        "name": _("Delete group"),
        "object_description": _("Delete this group."),
        "global_description": _("Delete any group in the system."),
        "ui_category": _("Groups"),
    },
    "galaxy.view_group": {
        "name": _("View group"),
        "object_description": _("View this group."),
        "global_description": _("View any existing group in the system."),
        "ui_category": _("Groups"),
    },
    "ansible.view_collectionremote": {
        "name": _("View collection remote"),
        "object_description": _("View this collection remote."),
        "global_description": _("View any collection remote existing in the system."),
        "ui_category": _("Collection Remotes"),
    },
    "ansible.add_collectionremote": {
        "name": _("Add collection remote"),
        "object_description": _("Add this collection remote."),
        "global_description": _("Add any collection remote existing in the system."),
        "ui_category": _("Collection Remotes"),
    },
    "ansible.change_collectionremote": {
        "name": _("Change collection remote"),
        "object_description": _("Edit this collection remote."),
        "global_description": _("Edit any collection remote existing in the system."),
        "ui_category": _("Collection Remotes"),
    },
    "ansible.delete_collectionremote": {
        "name": _("Delete collection remote"),
        "object_description": _("Delete this collection remote."),
        "global_description": _("Delete any collection remote existing in the system."),
        "ui_category": _("Collection Remotes"),
    },
    "ansible.manage_roles_collectionremote": {
        "name": _("Manage remote roles"),
        "object_description": _("Configure who has permissions on this remote."),
        "global_description": _("Configure who has permissions on any remote."),
        "ui_category": _("Collection Remotes"),
    },
    "ansible.view_ansiblerepository": {
        "name": _("View Ansible repository"),
        "object_description": _("View this Ansible repository."),
        "global_description": _("View any Ansible repository existing in the system."),
        "ui_category": _("Ansible Repository"),
    },
    "ansible.add_ansiblerepository": {
        "name": _("Add Ansible repository"),
        "object_description": _("Add this Ansible repository."),
        "global_description": _("Add any Ansible repository existing in the system."),
        "ui_category": _("Ansible Repository"),
    },
    "ansible.change_ansiblerepository": {
        "name": _("Change Ansible repository"),
        "object_description": _("Change this Ansible repository."),
        "global_description": _("Change any Ansible repository existing in the system."),
        "ui_category": _("Ansible Repository"),
    },
    "ansible.delete_ansiblerepository": {
        "name": _("Delete Ansible repository"),
        "object_description": _("Delete this Ansible repository."),
        "global_description": _("Delete any Ansible repository existing in the system."),
        "ui_category": _("Ansible Repository"),
    },
    "ansible.manage_roles_ansiblerepository": {
        "name": _("Manage repository roles"),
        "object_description": _("Configure who has permissions on this repository."),
        "global_description": _("Configure who has permissions on any repository."),
        "ui_category": _("Ansible Repository"),
    },
    "ansible.repair_ansiblerepository": {
        "name": _("Repair Ansible repository"),
        "object_description": _("Repair artifacts associated with this Ansible repository."),
        "global_description": _(
            "Repair artifacts associated with any Ansible repository existing in the system."
        ),
        "ui_category": _("Ansible Repository"),
    },
    "container.change_containernamespace": {
        "name": _("Change container namespace permissions"),
        "object_description": _("Edit permissions on this container namespace."),
        "global_description": _("Edit permissions on any existing container namespace."),
        "ui_category": _("Execution Environments"),
    },
    "container.namespace_change_containerdistribution": {
        "name": _("Change containers"),
        "object_description": _("Edit all objects in this container namespace."),
        "global_description": _("Edit all objects in any container namespace in the system."),
        "ui_category": _("Execution Environments"),
    },
    "container.namespace_modify_content_containerpushrepository" : {
        "name": _("Change image tags"),
        "object_description": _("Edit an image's tag in this container namespace"),
        "global_description": _("Edit an image's tag in any container namespace the system."),
        "ui_category": _("Execution Environments"),
    },
    "container.add_containernamespace": {
        "name": _("Create new containers"),
        "object_description": None,
        "global_description": _("Add new containers to the system."),
        "ui_category": _("Execution Environments"),
    },
    "container.delete_containerrepository": {
        "name": _("Delete container repository"),
        "object_description": _("Delete this container repository."),
        "global_description": _("Delete any existing container repository in the system."),
        "ui_category": _("Execution Environments"),
    },
    "container.namespace_push_containerdistribution": {
        "name": _("Push to existing containers"),
        "object_description": _("Push to this namespace."),
        "global_description": _("Push to any existing namespace in the system."),
        "ui_category": _("Execution Environments"),
    },
    "container.namespace_add_containerdistribution": {
        "name": _("Push new containers"),
        "object_description": _("Push a new container to this namespace."),
        "global_description": _("Push a new containers to any namespace in the system."),
        "ui_category": _("Execution Environments"),
    },
    "container.manage_roles_containernamespace": {
        "name": _("Manage container namespace roles"),
        "object_description": _("Manage container namespace roles."),
        "global_description": _("Manage container namespace roles existing in the system."),
        "ui_category": _("Execution Environments"),
    },
    "galaxy.add_containerregistryremote": {
        "name": _("Add remote registry"),
        "object_description": None,
        "global_description": _("Add remote registry to the system."),
        "ui_category": _("Container Registry Remotes"),
    },
    "galaxy.change_containerregistryremote": {
        "name": _("Change remote registry"),
        "object_description": _("Edit this remote registry."),
        "global_description": _("Change any remote registry existing in the system."),
        "ui_category": _("Container Registry Remotes"),
    },
    "galaxy.delete_containerregistryremote": {
        "name": _("Delete remote registry"),
        "object_description": _("Delete this remote registry."),
        "global_description": _("Delete any remote registry existing in the system."),
        "ui_category": "Container Registry Remotes",
    },
    "core.change_task": {
        "name": _("Change task"),
        "object_description": _("Edit this task."),
        "global_description": _("Edit any task existing in the system."),
        "ui_category": _("Task Management"),
    },
    "core.delete_task": {
        "name": _("Delete task"),
        "object_description": _("Delete this task."),
        "global_description": _("Delete any task existing in the system."),
        "ui_category": _("Task Management"),
    },
    "core.view_task": {
        "name": _("View all tasks"),
        "object_description": _("View this task."),
        "global_description": _("View any task existing in the system."),
        "ui_category": _("Task Management"),
    },
}

AAP_VERSION_FILE_PATH = '/etc/ansible-automation-platform/VERSION'
