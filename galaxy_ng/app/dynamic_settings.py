"""
type:
default:
description:
choices:
key_hints:
value_hints:
"""
DYNAMIC_SETTINGS_SCHEMA = {
    "FOO": {  # for testing
        "type": str,
        "default": "bar",
        "description": "Foo bar",
        "value_hints": ["bar", "baz"],
    },
    "GALAXY_REQUIRE_CONTENT_APPROVAL": {
        "type": bool,
        "default": False,
        "description": "Require content approval before it can be published",
        "choices": [True, False],
    },
    "GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL": {
        "type": bool,
        "default": False,
        "description": "Require signature for content approval",
        "choices": [True, False],
    },
    "GALAXY_SIGNATURE_UPLOAD_ENABLED": {
        "type": bool,
        "default": False,
        "description": "Enable signature upload",
        "choices": [True, False],
    },
    "GALAXY_AUTO_SIGN_COLLECTIONS": {
        "type": bool,
        "default": False,
        "description": "Automatically sign collections during approval/upload",
        "choices": [True, False],
    },
    "GALAXY_FEATURE_FLAGS": {
        "type": dict,
        "default": {},
        "description": "Feature flags for galaxy_ng",
        "key_hints": {
            "execution_environments": {
                "type": bool,
                "default": False,
                "description": "Enable execution environments",
                "choices": [True, False],
            },
        }
    },
    # For 1816 PR
    "INSIGHTS_TRACKING_STATE": {},
    "AUTOMATION_ANALYTICS_URL": {},
    "REDHAT_USERNAME": {},
    "REDHAT_PASSWORD": {},
    "AUTOMATION_ANALYTICS_LAST_GATHERED": {},
    "AUTOMATION_ANALYTICS_LAST_ENTRIES": {},
}
