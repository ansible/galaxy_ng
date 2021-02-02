STANDALONE_STATEMENTS = {
    'NamespaceViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "destroy",
            "principal": "*",
            "effect": "deny",
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
    'CollectionViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "destroy",
            "principal": "*",
            "effect": "deny",
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_create_collection"
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "can_update_collection"
        },
        {
            "action": "move_content",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:ansible.modify_ansible_repo_content"
        }
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
            "action": ["retrieve", "update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_current_user"
        },
    ],
    'SyncListViewSet': [
        #  disable synclists for on prem installations
        {
            "action": ["*"],
            "principal": "*",
            "effect": "deny",
        },
    ],
    'MySyncListViewSet': [
        #  disable synclists for on prem installations
        {
            "action": ["*"],
            "principal": "*",
            "effect": "deny",
        },
    ],
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
    'GroupViewSet': [
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
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.update_group"
        },
    ],
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
}
