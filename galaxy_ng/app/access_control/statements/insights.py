import copy
from galaxy_ng.app.access_control.statements.standalone import STANDALONE_STATEMENTS


_deny_all = [
    {
        "principal": "*",
        "action": "*",
        "effect": "deny"
    },
]

_signature_upload_statements = [
    {
        "action": ["list", "retrieve", "create"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": [
            "has_model_perms:ansible.modify_ansible_repo_content",
        ],
    },
]

_INSIGHTS_STATEMENTS = {
    **copy.deepcopy(STANDALONE_STATEMENTS),

    'content/ansible/collection_signatures': _signature_upload_statements,
    'AIDenyIndexView': _deny_all,

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
    "LegacyAccessPolicy": _deny_all,

    "UserViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.view_user"],
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.change_user"],
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
            "condition": ["has_model_perms:galaxy.view_synclist"],
        },
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_or_obj_perms:galaxy.view_synclist"],
        },
        {
            "action": ["destroy"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.delete_synclist"],
        },
        {
            "action": ["create"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.add_synclist"],
        },
        {
            "action": ["update", "partial_update"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["has_model_perms:galaxy.change_synclist"],
        },
    ],
    "MySyncListViewSet": [
        {
            "action": ["retrieve", "list", "update", "partial_update", "curate"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": ["is_org_admin"],
        },
    ],
    "GroupViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    "DistributionViewSet": _deny_all,
    "MyDistributionViewSet": [
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    "ContainerRepositoryViewSet": _deny_all,
    'ContainerReadmeViewset': _deny_all,
    'ContainerRegistryRemoteViewSet': _deny_all,
    'ContainerRemoteViewSet': _deny_all,


    "LandingPageViewSet": [
        {
            "action": ["retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
}


def _entitelify(policy):
    new_policy = {}

    for view in policy:
        statements = []
        for statement in policy[view]:
            new_statement = {**statement}

            # don't set conditions on deny statements. Otherwise, that will make it so
            # that users will only get denied if they have entitleements.
            if new_statement["effect"] == "allow":
                condition = new_statement.get("condition", None)

                if condition is None:
                    new_statement["condition"] = ["has_rh_entitlements"]
                elif isinstance(condition, list):
                    if "has_rh_entitlements" not in condition:
                        new_statement["condition"].append("has_rh_entitlements")
                elif isinstance(condition, str):
                    new_statement["condition"] = list({condition, "has_rh_entitlements"})

            statements.append(new_statement)

        new_policy[view] = statements

    return new_policy


INSIGHTS_STATEMENTS = _entitelify(_INSIGHTS_STATEMENTS)
