# Pulp ansible has the collections api broken down into a bunch of separate viewsets
# (ie: collection versions, collections, download, upload etc.) Galaxy NG expects the
# functionality of these viewsets to all be roughly the same, so instead of duplicating
# the statenents for these viewsets, they're stored here and reused on a bunch of different
# policies.

from galaxy_ng.app.access_control.statements.legacy import LEGACY_STATEMENTS

_collection_statements = [
    {
        "action": "list",
        "principal": "authenticated",
        "effect": "allow",
        "condition": "v3_can_view_repo_content"
    },
    {
        "action": "list",
        "principal": "anonymous",
        "effect": "allow",
        "condition": ["unauthenticated_collection_access_enabled", "v3_can_view_repo_content"],
    },
    {
        "action": "retrieve",
        "principal": "authenticated",
        "effect": "allow",
        "condition": "v3_can_view_repo_content",
    },
    {
        "action": "retrieve",
        "principal": "anonymous",
        "effect": "allow",
        "condition": ["unauthenticated_collection_access_enabled", "v3_can_view_repo_content"],
    },
    {
        "action": "destroy",
        "principal": "authenticated",
        "effect": "allow",
        "condition": ["has_model_perms:ansible.delete_collection", "v3_can_view_repo_content"],
    },
    {
        "action": ["download"],
        "principal": 'authenticated',
        "effect": "allow",
        "condition": "v3_can_view_repo_content"
    },
    {
        "action": ["download"],
        "principal": 'anonymous',
        "effect": "allow",
        "condition": ["unauthenticated_collection_download_enabled", "v3_can_view_repo_content"],
    },
    {
        "action": "create",
        "principal": "authenticated",
        "effect": "allow",
        "condition": ["can_create_collection", "v3_can_view_repo_content"],
    },
    {
        "action": "update",
        "principal": "authenticated",
        "effect": "allow",
        "condition": ["can_update_collection", "v3_can_view_repo_content"]
    },
    {
        "action": ["copy_content", "move_content"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "has_model_perms:ansible.modify_ansible_repo_content", "v3_can_view_repo_content"]
    },
    {
        "action": "sign",
        "principal": "authenticated",
        "effect": "allow",
        "condition": ["can_sign_collections", "v3_can_view_repo_content"]
    }
]

_group_statements = [
    {
        "action": ["list", "retrieve"],
        "principal": "authenticated",
        "effect": "allow",
    },
    {
        "action": "destroy",
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_model_perms:galaxy.delete_group"
    },
    {
        "action": "create",
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_model_perms:galaxy.add_group"
    },
    {
        "action": ["update", "partial_update"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_model_perms:galaxy.update_group"
    },
]

_deny_all = [
    {
        "principal": "*",
        "action": "*",
        "effect": "deny"
    },
]

_read_only = [
    {
        "action": ["list", "retrieve"],
        "principal": "authenticated",
        "effect": "allow",
    },
]

STANDALONE_STATEMENTS = {
    'CollectionViewSet': _collection_statements,

    "AppRootViewSet": [
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["retrieve"],
            "principal": "anonymous",
            "effect": "allow",
            "condition": "unauthenticated_collection_download_enabled",
        },
    ],

    'AIDenyIndexView': [
        {
            "action": ["ai-deny-index-list"],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": ["ai-deny-index-add", "ai-deny-index-delete"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_edit_ai_deny_index",
        },
    ],

    'NamespaceViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["list", "retrieve"],
            "principal": "anonymous",
            "effect": "allow",
            "condition": ["unauthenticated_collection_access_enabled"]
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:galaxy.delete_namespace"
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.add_namespace"
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:galaxy.change_namespace"
        },
    ],
    'CollectionRemoteViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow"
        },
        {
            "action": ["sync", "update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:ansible.change_collectionremote"
        }
    ],
    'UserViewSet': [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.view_user"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.view_user"
        },
        {
            "action": "destroy",
            "principal": "*",
            "effect": "deny",
            "condition": ["user_is_superuser"]
        },
        {
            "action": "destroy",
            "principal": "*",
            "effect": "deny",
            "condition": ["is_current_user"]
        },
        {
            "action": "destroy",
            "principal": "*",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.delete_user"
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.add_user"
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.change_user"
        },
    ],
    'MyUserViewSet': [
        {
            "action": ["retrieve"],
            "principal": "anonymous",
            "effect": "allow",
            "condition": "unauthenticated_collection_access_enabled"
        },
        {
            "action": ["retrieve", "update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_current_user"
        },
    ],
    #  disable synclists for on prem installations
    'SyncListViewSet': _deny_all,
    #  disable synclists for on prem installations
    'MySyncListViewSet': _deny_all,
    'TaskViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    'TagViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    # LoginView, LogoutView and TokenView are all views instead of viewsets.
    # At the moment, DRF access policy doesn't seem to be able to correctly
    # determine the action for views, so we have to resort to using *
    'LoginView': [
        {
            "action": ['*'],
            "principal": "*",
            "effect": "allow",
        }
    ],
    'LogoutView': [
        {
            "action": ['*'],
            "principal": "*",
            "effect": "allow"
        }
    ],
    'TokenView': [
        {
            "action": ['*'],
            "principal": "authenticated",
            "effect": "allow"
        }
    ],
    'GroupViewSet': _group_statements,
    'DistributionViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    'MyDistributionViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    # TODO: More specific permissions will be required here when pulp_container
    # RBAC is added
    'ContainerRepositoryViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:container.delete_containerrepository",
        },
    ],

    # The container readme can't just use the ContainerRepository access policies
    # because the readme viewset returns a readme object and not a container
    # repository object, which breaks has_model_or_obj_perms.
    'ContainerReadmeViewset': [
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": ["update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ("has_container_namespace_perms:"
                          "container.namespace_change_containerdistribution")
        },
    ],

    'ContainerRegistryRemoteViewSet': [
        # prevents deletion of registry
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.delete_containerregistryremote"
        },
        # allows authenticated users to VIEW registries
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        # allows users with model create permissions to create new registries
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.add_containerregistryremote"
        },
        {
            "action": "sync",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.change_containerregistryremote"
        },
        # allows users with model create permissions to update registries
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.change_containerregistryremote"
        },
        {
            "action": "index_execution_environments",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.change_containerregistryremote"
        },
    ],

    'ContainerRemoteViewSet': [
        # The permissions for creating namespaces are used as a proxy for creating containers,
        # so allow users to create container remotes if they have create namespace permissions.
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:container.add_containernamespace"
        },
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            # Permissions for containers are controlled via container distributions and namespaces.
            # Since the remote controls what will go into the container distribution, reuse the
            # same permissions here.
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distro_permission:container.change_containerdistribution"
        },
        {
            "action": "sync",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distro_permission:container.change_containerdistribution"
        },
    ],
}

STANDALONE_STATEMENTS.update(LEGACY_STATEMENTS)
