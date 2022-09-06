LEGACY_STATEMENTS = {
    "LegacyAccessPolicy": [
        {
            "action": [
                "get",
                "get_task",
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
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_namespace_owner",
        },
    ]
}
