DYNAMIC_SETTINGS_SCHEMA = {
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
        "choices": [],
        "hints": {
            "execution_environments": {
                "type": bool,
                "default": False,
                "description": "Enable execution environments",
                "choices": [True, False],
            },
        }
    },
}
