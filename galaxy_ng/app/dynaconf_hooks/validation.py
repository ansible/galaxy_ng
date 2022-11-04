from dynaconf import Dynaconf, Validator


def validate(settings: Dynaconf) -> None:
    """Validate the configuration, raise ValidationError if invalid"""
    settings.validators.register(
        Validator(
            "GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL",
            eq=False,
            when=Validator(
                "GALAXY_REQUIRE_CONTENT_APPROVAL", eq=False,
            ),
            messages={
                "operations": "{name} cannot be True if GALAXY_REQUIRE_CONTENT_APPROVAL is False"
            },
        ),
    )

    # AUTHENTICATION BACKENDS
    presets = settings.get("AUTHENTICATION_BACKEND_PRESETS_DATA", {})
    settings.validators.register(
        Validator(
            "AUTHENTICATION_BACKEND_PRESET",
            is_in=["local", "custom"] + list(presets.keys()),
        )
    )

    settings.validators.validate()
