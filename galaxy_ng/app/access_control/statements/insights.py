# Pulp ansible has the collections api broken down into a bunch of separate viewsets
# (ie: collection versions, collections, download, upload etc.) Galaxy NG expects the
# functionality of these viewsets to all be roughly the same, so instead of duplicating
# the statenents for these viewsets, they're stored here and reused on a bunch of different
# policies.
_collection_statements = [
    {
        "action": ["list", "retrieve"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_rh_entitlements",
    },
    {
        "action": "destroy",
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "has_model_perms:ansible.delete_collection",
            "has_rh_entitlements",
        ],
    },
    {
        "action": ["download"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_rh_entitlements",
    },
    {
        "action": "create",
        "principal": "authenticated",
        "effect": "allow",
        "condition": ["can_create_collection", "has_rh_entitlements"],
    },
    {
        "action": "update",
        "principal": "authenticated",
        "effect": "allow",
        "condition": ["can_update_collection", "has_rh_entitlements"],
    },
    {
        "action": "move_content",
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "has_model_perms:ansible.modify_ansible_repo_content",
            "has_rh_entitlements",
        ],
    },
    {
        "action": "curate",
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "has_model_perms:ansible.modify_ansible_repo_content",
            "has_rh_entitlements",
        ],
    },
    {
        "action": "sign",
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "can_sign_collections",
            "has_rh_entitlements"]
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

_signature_upload_statements = [
    {
        "action": ["list", "retrieve", "create"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "has_model_perms:ansible.modify_ansible_repo_content",
            "has_rh_entitlements",
        ],
    },
]

INSIGHTS_STATEMENTS = {
    'CollectionViewSet': _collection_statements,
    'pulp_ansible/v3/collections': _collection_statements,
    'pulp_ansible/v3/collection-versions': _collection_statements,
    'pulp_ansible/v3/collection-versions/docs': _collection_statements,
    'pulp_ansible/v3/collections/imports': _collection_statements,
    'pulp_ansible/v3/repo-metadata': _collection_statements,

    'repositories/ansible/ansible': _read_only,
    'content/ansible/collection_signatures': _signature_upload_statements,

    # The following endpoints are related to issue https://issues.redhat.com/browse/AAH-224
    # For now endpoints are temporary deactivated
    'pulp_ansible/v3/collection-versions/all': _deny_all,
    'pulp_ansible/v3/collections/all': _deny_all,

    # disable upload and download APIs since we're not using them yet
    'pulp_ansible/v3/collections/upload': _deny_all,
    'pulp_ansible/v3/collections/download': _deny_all,

    # The pulp viewsets are now accessible in GALAXY_DEPLOYMENT_MODE=insights
    # via the pulpcore api rerouted under api/automation-hub/
    # The following pulpcore viewsets are not needed in insights mode, and their
    # access policy allows `list` to all authenticated users.
    # We will deny these viewsets.
    "contentguards/core/rbac": _deny_all,
    "content/container/blobs": _deny_all,
    "remotes/container/container": _deny_all,
    "repositories/container/container": _deny_all,
    "content/container/manifests": _deny_all,
    "content/container/tags": _deny_all,

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

    "NamespaceViewSet": [
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
            "condition": ["has_model_perms:galaxy.add_namespace", "has_rh_entitlements"],
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_or_obj_perms:galaxy.delete_namespace", "has_rh_entitlements"],
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_or_obj_perms:galaxy.change_namespace", "has_rh_entitlements"],
        },
    ],
    "CollectionRemoteViewSet": [
        {"action": ["list", "retrieve"], "principal": "authenticated", "effect": "allow"},
        {
            "action": ["sync", "update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:ansible.change_collectionremote",
        },
    ],
    "UserViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.view_user", "has_rh_entitlements"],
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.change_user", "has_rh_entitlements"],
        },
        {
            "action": ["create", "destroy"],
            "principal": "*",
            "effect": "deny",
        },
    ],
    "MyUserViewSet": [
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_current_user",
        },
    ],
    "SyncListViewSet": [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.view_synclist", "has_rh_entitlements"],
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_or_obj_perms:galaxy.view_synclist", "has_rh_entitlements"],
        },
        {
            "action": ["destroy"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.delete_synclist", "has_rh_entitlements"],
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.add_synclist", "has_rh_entitlements"],
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.change_synclist", "has_rh_entitlements"],
        },
    ],
    "MySyncListViewSet": [
        {
            "action": ["retrieve", "list", "update", "partial_update", "curate"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_rh_entitlements", "is_org_admin"],
        },
    ],
    "TaskViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    "TagViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    "GroupViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
    ],
    "DistributionViewSet": _deny_all,
    "MyDistributionViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
    ],
    "ContainerRepositoryViewSet": _deny_all,
    "LandingPageViewSet": [
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_rh_entitlements",
        },
    ],

    'groups/roles': [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.change_group"
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.change_group"
        },
        {
            "action": "*",
            "principal": "admin",
            "effect": "allow"
        }
    ],
    'roles': [
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "*",
            "principal": "admin",
            "effect": "allow"
        }
    ]
}
