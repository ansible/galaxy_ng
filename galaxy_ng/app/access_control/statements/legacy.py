LEGACY_STATEMENTS = {
    "LegacyAccessPolicy": [
        {
            "action": ["get_task", "list", "retrieve"],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": ["create", "destroy"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_namespace_owner",
        },
    ]
}
