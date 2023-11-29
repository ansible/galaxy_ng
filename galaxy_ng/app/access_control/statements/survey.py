SURVEY_STATEMENTS = {
    "SurveyAccessPolicy": [
        {
            "action": [
                "get",
                "list",
                "retrieve",
                "create",
                # "update",
            ],
            "principal": "authenticated",
            "effect": "allow",
            # "condition": "is_survey_user",
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
            # "condition": "is_survey_user",
        },
    ]
}
