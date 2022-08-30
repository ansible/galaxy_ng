LEGACY_STATEMENTS = {
    "LegacyAccessPolicy": [
        {
            "action": [
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
                "destroy",
                "update_owners",
                "delete_namespace"
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_namespace_owner",
        },
    ]
}
