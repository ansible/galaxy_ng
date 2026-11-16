LEGACY_STATEMENTS = {
    "LegacyAccessPolicy": [
        {
            "action": [
                "get",
                "get_task",
                "list",
                "retrieve",
            ],
            # Legacy role reads stay anonymous so tokenless
            # `ansible-galaxy role install/search` keeps working
            # (community Galaxy compatibility).
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
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "is_namespace_owner",
        },
    ]
}
