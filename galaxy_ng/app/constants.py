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

ROLE_DESCRIPTION = {
    # Core roles from pulpcore
    "core.compositecontentguard_creator": "Create composite content guards.",
    "core.compositecontentguard_owner": "Manage composite content guards with full access.",
    "core.compositecontentguard_viewer": "View composite content guards.",
    "core.contentredirectcontentguard_creator": "Create content redirect content guards.",
    "core.contentredirectcontentguard_owner": (
        "Manage content redirect content guards with full access."
    ),
    "core.contentredirectcontentguard_viewer": "View content redirect content guards.",
    "core.domain_creator": "Create domains.",
    "core.domain_owner": "Manage domains with full access.",
    "core.domain_viewer": "View domains.",
    "core.group_creator": "Create user groups.",
    "core.group_owner": "Manage user groups with full access.",
    "core.group_viewer": "View user groups.",
    "core.headercontentguard_creator": "Create header content guards.",
    "core.headercontentguard_owner": "Manage header content guards with full access.",
    "core.headercontentguard_viewer": "View header content guards.",
    "core.rbaccontentguard_creator": "Create RBAC content guards.",
    "core.rbaccontentguard_owner": "Manage RBAC content guards with full access.",
    "core.rbaccontentguard_viewer": "View RBAC content guards.",
    "core.rbaccontentguard_downloader": "Download content through RBAC content guards.",
    "core.taskschedule_viewer": "View task schedule details.",
    "core.task_viewer": "View task details and status.",
    "core.task_user_dispatcher": "Dispatch and create new tasks.",
    "core.upload_creator": "Create file uploads.",
    "core.upload_owner": "Manage file uploads with full access.",
    "core.upload_viewer": "View file uploads.",
    "core.upstreampulp_creator": "Create upstream Galaxy servers for replication.",
    "core.upstreampulp_owner": (
        "Manage upstream Galaxy servers with full access including replication."
    ),
    "core.upstreampulp_viewer": "View upstream Galaxy server configurations.",
    "core.upstreampulp_user": "Use upstream Galaxy servers for replication tasks.",
    # Container roles from pulp_container
    "container.containerdistribution_creator": "Create new container distributions.",
    "container.containerdistribution_owner": (
        "Manage all aspects of container distributions including viewing, pulling, "
        "pushing, deleting, modifying configurations, and managing user roles."
    ),
    "container.containerdistribution_collaborator": (
        "Collaborate on container distributions with permissions to view, pull, and push content."
    ),
    "container.containerdistribution_consumer": (
        "Consume container distributions with read-only access to view and pull content."
    ),
    "container.containernamespace_creator": "Create new container namespaces.",
    "container.containernamespace_owner": (
        "Manage all aspects of container namespaces including viewing, deleting, managing "
        "distributions and repositories within the namespace, modifying content, "
        "and managing user roles."
    ),
    "container.containernamespace_collaborator": (
        "Collaborate on container namespaces with permissions to view, manage distributions "
        "and repositories, modify content, and perform push/pull operations."
    ),
    "container.containernamespace_consumer": (
        "Consume container namespaces with read-only access to view and pull content."
    ),
    "container.containerpullthroughdistribution_creator": (
        "Create new pull-through container distributions for caching external content."
    ),
    "container.containerpullthroughdistribution_owner": (
        "Manage all aspects of pull-through container distributions including viewing, deleting, "
        "modifying configurations, managing user roles, and pulling new content."
    ),
    "container.containerpullthroughdistribution_collaborator": (
        "Collaborate on pull-through container distributions with permissions "
        "to view and pull new content."
    ),
    "container.containerpullthroughdistribution_consumer": (
        "Consume pull-through container distributions with read-only access "
        "to view and pull new content."
    ),
    "container.containerpullthroughremote_creator": (
        "Create new pull-through container remotes for caching external registries."
    ),
    "container.containerpullthroughremote_owner": (
        "Manage all aspects of pull-through container remotes including viewing, "
        "modifying, deleting, and managing user roles."
    ),
    "container.containerpullthroughremote_viewer": (
        "View pull-through container remote configurations and details."
    ),
    "container.containerremote_creator": "Create new container remotes.",
    "container.containerremote_owner": (
        "Manage all aspects of container remotes including viewing, modifying, "
        "deleting, and managing user roles."
    ),
    "container.containerremote_viewer": "View container remote configurations and details.",
    "container.containerrepository_creator": "Create new container repositories.",
    "container.containerrepository_owner": (
        "Manage all aspects of container repositories including viewing, modifying, deleting, "
        "syncing, content management, image building, and user role management."
    ),
    "container.containerrepository_content_manager": (
        "Manage container repository content including viewing, syncing, modifying content, "
        "building images, and deleting repository versions."
    ),
    "container.containerrepository_viewer": "View container repository details and configurations.",
    # Ansible roles from pulp_ansible
    "ansible.ansibledistribution_creator": (
        "Allows you to create new Ansible distributions for serving collections "
        "and roles to clients."
    ),
    "ansible.ansibledistribution_owner": (
        "Allows you to view, edit, delete, and manage roles for Ansible distributions."
    ),
    "ansible.ansibledistribution_viewer": "Allows you to view Ansible distribution.",
    "ansible.ansiblerepository_creator": (
        "Allows you to create new Ansible repositories for storing collections and roles."
    ),
    "ansible.ansiblerepository_owner": (
        "Allows you to view, edit, delete, and manage all aspects of Ansible repositories "
        "including content modification, syncing, signing, and metadata operations."
    ),
    "ansible.ansiblerepository_viewer": (
        "Allows you to view Ansible repository information and contents."
    ),
    "ansible.collectionremote_creator": (
        "Allows you to create new collection remotes for syncing Ansible collections "
        "from external sources."
    ),
    "ansible.collectionremote_owner": (
        "Allows you to view, edit, delete, and manage roles for collection remotes."
    ),
    "ansible.collectionremote_viewer": "Allows you to view collection remote.",
    "ansible.gitremote_creator": (
        "Allows you to create new git remote for syncing Ansible content from git repository."
    ),
    "ansible.gitremote_owner": (
        "Allows you to view, edit, delete, and manage roles for git remote."
    ),
    "ansible.gitremote_viewer": "Allows you to view git remote.",
    "ansible.roleremote_creator": "Allows you to create new role remote for syncing Ansible roles.",
    "ansible.roleremote_owner": (
        "Allows you to view, edit, delete, and manage roles for role remote."
    ),
    "ansible.roleremote_viewer": "Allows you to view role remote.",
}
