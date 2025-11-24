import copy
import os
from unittest.mock import Mock, patch
import pytest

from galaxy_ng.app.dynaconf_hooks import (
    post as post_hook,
    configure_cors,
    configure_logging,
    configure_socialauth,
    configure_renderers,
    configure_legacy_roles,
    configure_dynamic_settings,
)


class SuperDict(dict):

    immutable = False

    _loaded_files = []
    _loaded_envs = []
    _loaded_hooks = {}
    _loaded_by_loaders = {}

    @property
    def _store(self):
        return self

    def as_dict(self):
        return self

    def set(self, key, value):
        if self.immutable:
            raise Exception("not mutable!")
        self[key] = value

    # REVIEW(cutwater): Why this method is needed?
    def get(self, key, default=None):
        return self[key] if key in self else default  # noqa: SIM401

    def __getattr__(self, key):
        try:
            # If key exists in the dictionary, return it
            return self[key]
        except KeyError:
            # Raise an attribute error if the key doesn't exist
            raise AttributeError(f"'CustomDict' object has no attribute '{key}'")

    # This is called when setting an attribute that doesn't exist on the object
    def __setattr__(self, key, value):
        # Assign the value to the dictionary using the key
        if self.immutable:
            raise Exception("not mutable!")
        self[key] = value


class SuperValidator:
    @staticmethod
    def register(*args, **kwargs):
        pass

    @staticmethod
    def validate(*args, **kwargs):
        pass


AUTHENTICATION_BACKEND_PRESETS_DATA = {
    "ldap": [
        "galaxy_ng.app.auth.ldap.PrefixedLDAPBackend",
        # "galaxy_ng.app.auth.ldap.GalaxyLDAPBackend",
        "django.contrib.auth.backends.ModelBackend",
        "pulpcore.backends.ObjectRolePermissionBackend",
        "dynaconf_merge",
    ],
    "keycloak": [
        "social_core.backends.keycloak.KeycloakOAuth2",
        "dynaconf_merge",
    ],
}

BASE_SETTINGS = {
    "AUTH_PASSWORD_VALIDATORS": [],
    "GALAXY_API_PATH_PREFIX": "/api/galaxy",
    "INSTALLED_APPS": [],
    "REST_FRAMEWORK": True,
    "SPECTACULAR_SETTINGS": True,
    "AUTHENTICATION_BACKENDS": [],
    "MIDDLEWARE": None,
    "AUTHENTICATION_BACKEND_PRESETS_DATA": copy.deepcopy(AUTHENTICATION_BACKEND_PRESETS_DATA),
    "BASE_DIR": "templates",
    "validators": SuperValidator(),
    "TEMPLATES": [],
    "FLAGS": {},
}


@pytest.mark.parametrize(
    ("do_stuff", "extra_settings", "expected_results"),
    [
        # 0 >=4.10 no external auth ...
        (
            True,
            # False,
            {},
            {
                "AUTHENTICATION_BACKENDS": [
                    "ansible_base.lib.backends.prefixed_user_auth.PrefixedUserAuthBackend"
                ]
            },
        ),
        # 1 >=4.10 ldap ...
        (
            True,
            # False,
            {
                "AUTHENTICATION_BACKEND_PRESET": "ldap",
                "AUTH_LDAP_SERVER_URI": "ldap://ldap:10389",
                "AUTH_LDAP_BIND_DN": "cn=admin,dc=planetexpress,dc=com",
                "AUTH_LDAP_BIND_PASSWORD": "GoodNewsEveryone",
                "AUTH_LDAP_USER_SEARCH_BASE_DN": "ou=people,dc=planetexpress,dc=com",
                "AUTH_LDAP_USER_SEARCH_SCOPE": "SUBTREE",
                "AUTH_LDAP_USER_SEARCH_FILTER": "(uid=%(user)s)",
                "AUTH_LDAP_GROUP_SEARCH_BASE_DN": "ou=people,dc=planetexpress,dc=com",
                "AUTH_LDAP_GROUP_SEARCH_SCOPE": "SUBTREE",
                "AUTH_LDAP_GROUP_SEARCH_FILTER": "(objectClass=Group)",
                "AUTH_LDAP_USER_ATTR_MAP": {
                    "first_name": "givenName",
                    "last_name": "sn",
                    "email": "mail",
                },
            },
            {
                "GALAXY_AUTH_LDAP_ENABLED": True,
                "AUTH_LDAP_GLOBAL_OPTIONS": {},
                "AUTHENTICATION_BACKENDS": [
                    "galaxy_ng.app.auth.ldap.PrefixedLDAPBackend",
                    "django.contrib.auth.backends.ModelBackend",
                    "pulpcore.backends.ObjectRolePermissionBackend",
                    "dynaconf_merge",
                    "ansible_base.lib.backends.prefixed_user_auth.PrefixedUserAuthBackend",
                ],
                "ANSIBLE_AUTHENTICATION_CLASSES": None,
                "GALAXY_AUTHENTICATION_CLASSES": None,
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": None,
            },
        ),
        # 2 >=4.10 keycloak ...
        (
            True,
            # False,
            {
                "AUTHENTICATION_BACKEND_PRESET": "keycloak",
                "SOCIAL_AUTH_KEYCLOAK_KEY": "xyz",
                "SOCIAL_AUTH_KEYCLOAK_SECRET": "abc",
                "SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY": "1234",
                "KEYCLOAK_PROTOCOL": "http",
                "KEYCLOAK_HOST": "cloak.com",
                "KEYCLOAK_PORT": 8080,
                "KEYCLOAK_REALM": "aap",
            },
            {
                "GALAXY_AUTH_KEYCLOAK_ENABLED": True,
                "GALAXY_FEATURE_FLAGS__external_authentication": True,
                "AUTHENTICATION_BACKENDS": [
                    "social_core.backends.keycloak.KeycloakOAuth2",
                    "dynaconf_merge",
                    "ansible_base.lib.backends.prefixed_user_auth.PrefixedUserAuthBackend",
                ],
                "ANSIBLE_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token_auth.ExpiringTokenAuthentication",
                ],
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token_auth.ExpiringTokenAuthentication",
                ],
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token_auth.ExpiringTokenAuthentication",
                ],
            },
        ),
        # 3 >=4.10 dab ..
        (
            True,
            # False,
            {
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ]
            },
            {
                "AUTHENTICATION_BACKENDS": [
                    "ansible_base.lib.backends.prefixed_user_auth.PrefixedUserAuthBackend",
                ],
                "ANSIBLE_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
            },
        ),
        # 4 >=4.10 keycloak+dab ...
        (
            True,
            # False,
            {
                "AUTHENTICATION_BACKEND_PRESET": "keycloak",
                "SOCIAL_AUTH_KEYCLOAK_KEY": "xyz",
                "SOCIAL_AUTH_KEYCLOAK_SECRET": "abc",
                "SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY": "1234",
                "KEYCLOAK_PROTOCOL": "http",
                "KEYCLOAK_HOST": "cloak.com",
                "KEYCLOAK_PORT": 8080,
                "KEYCLOAK_REALM": "aap",
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
            },
            {
                "GALAXY_AUTH_KEYCLOAK_ENABLED": True,
                "GALAXY_FEATURE_FLAGS__external_authentication": True,
                "AUTHENTICATION_BACKENDS": [
                    "social_core.backends.keycloak.KeycloakOAuth2",
                    "dynaconf_merge",
                    "ansible_base.lib.backends.prefixed_user_auth.PrefixedUserAuthBackend",
                ],
                "ANSIBLE_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token_auth.ExpiringTokenAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token_auth.ExpiringTokenAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token_auth.ExpiringTokenAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
            },
        ),
        # 5 >=4.10 ldap+dab ...
        (
            True,
            # False,
            {
                "AUTHENTICATION_BACKEND_PRESET": "ldap",
                "AUTH_LDAP_SERVER_URI": "ldap://ldap:10389",
                "AUTH_LDAP_BIND_DN": "cn=admin,dc=planetexpress,dc=com",
                "AUTH_LDAP_BIND_PASSWORD": "GoodNewsEveryone",
                "AUTH_LDAP_USER_SEARCH_BASE_DN": "ou=people,dc=planetexpress,dc=com",
                "AUTH_LDAP_USER_SEARCH_SCOPE": "SUBTREE",
                "AUTH_LDAP_USER_SEARCH_FILTER": "(uid=%(user)s)",
                "AUTH_LDAP_GROUP_SEARCH_BASE_DN": "ou=people,dc=planetexpress,dc=com",
                "AUTH_LDAP_GROUP_SEARCH_SCOPE": "SUBTREE",
                "AUTH_LDAP_GROUP_SEARCH_FILTER": "(objectClass=Group)",
                "AUTH_LDAP_USER_ATTR_MAP": {
                    "first_name": "givenName",
                    "last_name": "sn",
                    "email": "mail",
                },
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
            },
            {
                "GALAXY_AUTH_LDAP_ENABLED": True,
                "AUTH_LDAP_GLOBAL_OPTIONS": {},
                "AUTHENTICATION_BACKENDS": [
                    "galaxy_ng.app.auth.ldap.PrefixedLDAPBackend",
                    "django.contrib.auth.backends.ModelBackend",
                    "pulpcore.backends.ObjectRolePermissionBackend",
                    "dynaconf_merge",
                    "ansible_base.lib.backends.prefixed_user_auth.PrefixedUserAuthBackend",
                ],
                "ANSIBLE_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
            },
        ),
    ],
)
def test_dynaconf_hooks_authentication_backends_and_classes(
    do_stuff,
    extra_settings,
    expected_results
):

    # skip test this way ...
    if not do_stuff:
        return

    xsettings = SuperDict()
    xsettings.update(copy.deepcopy(BASE_SETTINGS))
    if extra_settings:
        xsettings.update(copy.deepcopy(extra_settings))

    # don't allow the downstream to edit this data ...
    xsettings.immutable = True

    new_settings = post_hook(xsettings, run_dynamic=True, run_validate=True)
    for key, val in expected_results.items():
        """
        try:
            assert new_settings[key] == val
        except Exception as e:
            print(e)
            import epdb; epdb.st()
            print(e)
        """
        assert new_settings.get(key) == val


def test_dab_dynaconf():
    """Ensure that the DAB settings are correctly set."""

    xsettings = SuperDict()
    xsettings.update(copy.deepcopy(BASE_SETTINGS))

    # Run the post hook
    new_settings = post_hook(xsettings, run_dynamic=True, run_validate=True)

    # Check that DAB injected settings are correctly set
    expected_keys = [
        "ANSIBLE_BASE_OVERRIDDEN_SETTINGS",
        "ANSIBLE_STANDARD_SETTINGS_FILES",
        "ANSIBLE_BASE_OVERRIDABLE_SETTINGS",
        "IS_DEVELOPMENT_MODE",
        "CLI_DYNACONF",
        "DAB_DYNACONF",
    ]
    for key in expected_keys:
        assert key in new_settings


class TestConfigureCors:

    @patch.dict(os.environ, {"DEV_SOURCE_PATH": "/dev/path"})
    def test_configure_cors_enabled_in_dev(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=False: {
            "GALAXY_ENABLE_CORS": True,
            "MIDDLEWARE": ["existing.middleware"]
        }.get(key, default)

        result = configure_cors(mock_settings)

        assert "MIDDLEWARE" in result
        assert "galaxy_ng.app.common.openapi.AllowCorsMiddleware" in result["MIDDLEWARE"]

    @patch.dict(os.environ, {}, clear=True)
    def test_configure_cors_disabled_not_dev(self):
        mock_settings = Mock()
        mock_settings.get.return_value = True

        result = configure_cors(mock_settings)

        assert result == {}

    @patch.dict(os.environ, {"DEV_SOURCE_PATH": "/dev/path"})
    def test_configure_cors_disabled_in_dev(self):
        mock_settings = Mock()
        mock_settings.get.return_value = False

        result = configure_cors(mock_settings)

        assert result == {}


class TestConfigureLogging:

    def test_configure_logging_enabled_via_settings(self):
        mock_settings = Mock()
        mock_settings.get.return_value = True

        result = configure_logging(mock_settings)

        assert result["GALAXY_ENABLE_API_ACCESS_LOG"] is True
        assert "automated_logging" in result["INSTALLED_APPS"]
        assert "MIDDLEWARE" in result
        assert "LOGGING" in result
        assert "AUTOMATED_LOGGING" in result
        assert result["LOGGING"]["dynaconf_merge"] is True

    @patch.dict(os.environ, {"GALAXY_ENABLE_API_ACCESS_LOG": "True"})
    def test_configure_logging_enabled_via_env(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "GALAXY_ENABLE_API_ACCESS_LOG": True
        }.get(key, default)

        result = configure_logging(mock_settings)

        assert result["GALAXY_ENABLE_API_ACCESS_LOG"] is True

    def test_configure_logging_disabled(self):
        mock_settings = Mock()
        mock_settings.get.return_value = False

        result = configure_logging(mock_settings)

        assert result["GALAXY_ENABLE_API_ACCESS_LOG"] is False
        assert "INSTALLED_APPS" not in result


class TestConfigureSocialAuth:

    def test_configure_socialauth_enabled(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "SOCIAL_AUTH_GITHUB_KEY": "github_key",
            "SOCIAL_AUTH_GITHUB_SECRET": "github_secret",
            "AUTHENTICATION_BACKENDS": []
        }.get(key, default)

        result = configure_socialauth(mock_settings)

        assert result["GALAXY_FEATURE_FLAGS__external_authentication"] is True
        assert "social_django" in result["INSTALLED_APPS"]
        assert "galaxy_ng.social.GalaxyNGOAuth2" in result["AUTHENTICATION_BACKENDS"]
        assert "SOCIAL_AUTH_PIPELINE" in result
        assert "DEFAULT_AUTHENTICATION_CLASSES" in result
        assert "GALAXY_AUTHENTICATION_CLASSES" in result
        assert "REST_FRAMEWORK_AUTHENTICATION_CLASSES" in result

    def test_configure_socialauth_missing_key(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "SOCIAL_AUTH_GITHUB_SECRET": "github_secret"
        }.get(key, default)

        result = configure_socialauth(mock_settings)

        assert result == {}

    def test_configure_socialauth_missing_secret(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "SOCIAL_AUTH_GITHUB_KEY": "github_key"
        }.get(key, default)

        result = configure_socialauth(mock_settings)

        assert result == {}

    def test_configure_socialauth_disabled(self):
        mock_settings = Mock()
        mock_settings.get.return_value = None

        result = configure_socialauth(mock_settings)

        assert result == {}


class TestConfigureRenderers:

    def test_configure_renderers_galaxy_community(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default="": {
            "CONTENT_ORIGIN": "https://galaxy.ansible.com",
            "REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES": ["existing.renderer"]
        }.get(key, default)

        result = configure_renderers(mock_settings)

        assert (
            "galaxy_ng.app.renderers.CustomBrowsableAPIRenderer"
            in result["REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES"]
        )

    def test_configure_renderers_galaxy_dev(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default="": {
            "CONTENT_ORIGIN": "https://galaxy-dev.ansible.com",
            "REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES": []
        }.get(key, default)

        result = configure_renderers(mock_settings)

        assert (
            "galaxy_ng.app.renderers.CustomBrowsableAPIRenderer"
            in result["REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES"]
        )

    def test_configure_renderers_galaxy_stage(self):
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default="": {
            "CONTENT_ORIGIN": "https://galaxy-stage.ansible.com",
            "REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES": []
        }.get(key, default)

        result = configure_renderers(mock_settings)

        assert (
            "galaxy_ng.app.renderers.CustomBrowsableAPIRenderer"
            in result["REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES"]
        )

    def test_configure_renderers_not_community(self):
        mock_settings = Mock()
        mock_settings.get.return_value = "https://other.example.com"

        result = configure_renderers(mock_settings)

        assert result == {}

    def test_configure_renderers_empty_content_origin(self):
        mock_settings = Mock()
        mock_settings.get.return_value = ""

        result = configure_renderers(mock_settings)

        assert result == {}


class TestConfigureLegacyRoles:

    def test_configure_legacy_roles_enabled(self):
        mock_settings = Mock()
        mock_settings.get.return_value = True

        result = configure_legacy_roles(mock_settings)

        assert result["GALAXY_FEATURE_FLAGS__legacy_roles"] is True

    def test_configure_legacy_roles_disabled(self):
        mock_settings = Mock()
        mock_settings.get.return_value = False

        result = configure_legacy_roles(mock_settings)

        assert result["GALAXY_FEATURE_FLAGS__legacy_roles"] is False

    def test_configure_legacy_roles_default_false(self):
        mock_settings = Mock()
        mock_settings.get.return_value = False  # default value

        result = configure_legacy_roles(mock_settings)

        assert result["GALAXY_FEATURE_FLAGS__legacy_roles"] is False


class TestConfigureDynamicSettings:

    def test_configure_dynamic_settings_disabled(self):
        mock_settings = Mock()
        mock_settings.get.return_value = None

        result = configure_dynamic_settings(mock_settings)

        assert result == {}

    def test_configure_dynamic_settings_empty_list(self):
        mock_settings = Mock()
        mock_settings.get.return_value = []

        result = configure_dynamic_settings(mock_settings)

        assert result == {}

    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_configure_dynamic_settings_enabled(self, mock_apps):
        mock_apps.ready = True
        mock_settings = Mock()
        mock_settings.get.return_value = ["read_settings_from_cache_or_db"]

        # Mock the dynamic imports that happen inside configure_dynamic_settings
        mock_hook = Mock()
        mock_action = Mock()
        mock_action.AFTER_GET = 'after_get'

        with patch.dict('sys.modules', {
            'dynaconf.hooking': Mock(Hook=mock_hook, Action=mock_action, HookValue=Mock()),
            'dynaconf': Mock(DynaconfFormatError=Exception, DynaconfParseError=Exception),
            'dynaconf.base': Mock(Settings=Mock()),
            'dynaconf.loaders.base': Mock(SourceMetadata=Mock())
        }):
            result = configure_dynamic_settings(mock_settings)

        assert "_registered_hooks" in result
        mock_hook.assert_called_once()

    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_configure_dynamic_settings_multiple_hooks(self, mock_apps):
        mock_apps.ready = True
        mock_settings = Mock()
        mock_settings.get.return_value = [
            "read_settings_from_cache_or_db", "alter_hostname_settings"
        ]

        # Mock the dynamic imports that happen inside configure_dynamic_settings
        mock_hook = Mock()
        mock_action = Mock()
        mock_action.AFTER_GET = 'after_get'

        with patch.dict('sys.modules', {
            'dynaconf.hooking': Mock(Hook=mock_hook, Action=mock_action, HookValue=Mock()),
            'dynaconf': Mock(DynaconfFormatError=Exception, DynaconfParseError=Exception),
            'dynaconf.base': Mock(Settings=Mock()),
            'dynaconf.loaders.base': Mock(SourceMetadata=Mock())
        }):
            result = configure_dynamic_settings(mock_settings)

        assert "_registered_hooks" in result
        assert mock_hook.call_count == 2

    def test_configure_dynamic_settings_import_error(self):
        mock_settings = Mock()
        mock_settings.get.return_value = ["read_settings_from_cache_or_db"]

        # Simulate ImportError by making the specific imports fail
        def failing_import(name, *args, **kwargs):
            if 'dynaconf' in name:
                raise ImportError("test error")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=failing_import):
            result = configure_dynamic_settings(mock_settings)

        assert result == {}

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    def test_configure_dynamic_settings_logs_error_on_import(self, mock_logger):
        mock_settings = Mock()
        mock_settings.get.return_value = ["read_settings_from_cache_or_db"]

        # Simulate ImportError by making the specific imports fail
        def failing_import(name, *args, **kwargs):
            if 'dynaconf' in name:
                raise ImportError("test error")
            return __import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=failing_import):
            configure_dynamic_settings(mock_settings)

        mock_logger.error.assert_called_once()

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_configure_dynamic_settings_logs_info(self, mock_apps, mock_logger):
        mock_apps.ready = True
        mock_settings = Mock()
        mock_settings.get.return_value = ["read_settings_from_cache_or_db"]

        # Mock the dynamic imports that happen inside configure_dynamic_settings
        mock_hook = Mock()
        mock_action = Mock()
        mock_action.AFTER_GET = 'after_get'

        with patch.dict('sys.modules', {
            'dynaconf.hooking': Mock(Hook=mock_hook, Action=mock_action, HookValue=Mock()),
            'dynaconf': Mock(DynaconfFormatError=Exception, DynaconfParseError=Exception),
            'dynaconf.base': Mock(Settings=Mock()),
            'dynaconf.loaders.base': Mock(SourceMetadata=Mock())
        }):
            configure_dynamic_settings(mock_settings)

        mock_logger.info.assert_called_with("Enabling Dynamic Settings Feature")
