LEGACY_STATEMENTS = {
    "LegacyAccessPolicy": [
        {
            "action": [
                "get",
                "get_task",
                "get_owners",
                "list",
                "retrieve"
            ],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": [
                "create",
                "delete",
                "destroy",
                "update",
                "update_owners",
                "delete_namespace"
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_namespace_owner",
        },
    ]
}
