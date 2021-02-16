INSIGHTS_STATEMENTS = {
    'NamespaceViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.add_namespace", "has_rh_entitlements"]
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_or_obj_perms:galaxy.change_namespace",
                "has_rh_entitlements"]
        },
    ],
    'CollectionViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["can_create_collection", "has_rh_entitlements"]
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
            "condition": [
                "has_model_perms:ansible.modify_ansible_repo_content",
                "has_rh_entitlements"]
        },
        {
            "action": "curate",
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_perms:ansible.modify_ansible_repo_content",
                "has_rh_entitlements"]
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
            "action": ["*"],
            "principal": "authenticated",
            "effect": "deny",
        },
    ],
    'MyUserViewSet': [
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_current_user"
        },
    ],
    'SyncListViewSet': [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.view_synclist",
                          "has_rh_entitlements",
                          "is_org_admin"]
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_or_obj_perms:galaxy.view_synclist",
                "has_rh_entitlements",
                "is_org_admin"]
        },
        {
            "action": ["destroy"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_perms:galaxy.delete_synclist",
                "has_rh_entitlements",
                "is_org_admin"]
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_perms:galaxy.add_synclist",
                "has_rh_entitlements",
                "is_org_admin"]
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_or_obj_perms:galaxy.change_synclist",
                "has_rh_entitlements"]
        },
    ],
    'MySyncListViewSet': [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements"
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_or_obj_perms:galaxy.view_synclist",
                "has_rh_entitlements"]
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_or_obj_perms:galaxy.change_synclist",
                "has_rh_entitlements"]
        },
        {
            "action": ["curate"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": [
                "has_model_or_obj_perms:galaxy.change_synclist",
                "has_rh_entitlements"]
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
    'GroupViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
    ],
    'DistributionViewSet': [
        {
            "action": ["*"],
            "principal": "authenticated",
            "effect": "deny",
        },
    ],
    'MyDistributionViewSet': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
    ],
    'ContainerRepositoryViewSet': [
        {
            "action": ["*"],
            "principal": "*",
            "effect": "deny",
        },
    ],
}
