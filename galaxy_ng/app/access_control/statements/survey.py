SURVEY_STATEMENTS = {
    "SurveyAccessPolicy": [
        {
            "action": [
                "get",
                "list",
                "retrieve",
                "create",
            ],
            "principal": "authenticated",
            "effect": "allow",
        },
    ],
    "SurveyRollupAccessPolicy": [
        {
            "action": [
                "get",
                "list",
                "retrieve",
            ],
            "principal": "*",
            "effect": "allow",
        },
        {
            "action": [
                "create",
                "update",
            ],
            "principal": "authenticated",
            "effect": "allow",
        },
    ]
}
