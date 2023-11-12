from dynaconf import Validator

DYNAMIC_SETTINGS_SCHEMA = {
    "GALAXY_REQUIRE_CONTENT_APPROVAL": {
        "validator": Validator(is_type_of=bool),
        "schema": {
            "type": "boolean",
            "enum": ["true", "false"],
            "default": False,
            "description": "Require content approval before it can be published",
        }
    },
    "GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL": {
        "validator": Validator(is_type_of=bool),
        "schema": {
            "type": "boolean",
            "enum": ["true", "false"],
            "default": "false",
            "description": "Require signature for content approval",
        }
    },
    "GALAXY_SIGNATURE_UPLOAD_ENABLED": {
        "validator": Validator(is_type_of=bool),
        "schema": {
            "type": "boolean",
            "enum": ["true", "false"],
            "default": "false",
            "description": "Enable signature upload",
        }
    },
    "GALAXY_AUTO_SIGN_COLLECTIONS": {
        "validator": Validator(is_type_of=bool),
        "schema": {
            "type": "boolean",
            "enum": ["true", "false"],
            "default": "false",
            "description": "Automatically sign collections during approval/upload",
        }
    },
    "GALAXY_FEATURE_FLAGS": {
        "validator": Validator(is_type_of=dict),
        "schema": {
            "type": "object",
            "properties": {
                "execution_environments": {
                    "type": "boolean",
                    "enum": ["true", "false"],
                    "default": "false",
                    "description": "Enable execution environments",
                },
            },
            "default": {},
            "description": "Feature flags for galaxy_ng",
        },
    },
    # For 1816 PR
    "INSIGHTS_TRACKING_STATE": {},
    "AUTOMATION_ANALYTICS_URL": {},
    "REDHAT_USERNAME": {},
    "REDHAT_PASSWORD": {},
    "AUTOMATION_ANALYTICS_LAST_GATHERED": {},
    "AUTOMATION_ANALYTICS_LAST_ENTRIES": {},
    "FOO": {},
    "BAR": {},
}
