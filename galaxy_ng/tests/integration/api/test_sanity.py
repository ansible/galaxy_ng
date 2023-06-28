def test_tests_are_running_with_correct_auth_backend(ansible_config, settings):
    # Sanity test to ensure that the test environment is running with
    # the correct authentication backend
    config = ansible_config("admin")
    if config["auth_backend"] == "ldap":
        assert settings.get("GALAXY_AUTH_LDAP_ENABLED")
    elif config["auth_backend"] == "ldap":
        assert settings.get("KEYCLOAK_URL") is not None
    elif config["auth_backend"] == "galaxy":
        assert settings.get("GALAXY_AUTH_LDAP_ENABLED") is None
        assert settings.get("KEYCLOAK_URL") is None
