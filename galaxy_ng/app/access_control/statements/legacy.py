LEGACY_STATEMENTS = {
    "LegacyAccessPolicy": [
        {
            "action": [
                "get",
                "get_task",
                "list",
                "retrieve",
                "ai-deny-index-list",
            ],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": [
                "create",
                "delete",
                "delete_by_url_params",
                "destroy",
                "update",
                "ai-deny-index-add",
                "ai-deny-index-delete",
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_namespace_owner",
        },
    ]
}
