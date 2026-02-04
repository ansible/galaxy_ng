import copy
import os
from unittest.mock import Mock, patch
import pytest

from django.core.exceptions import SuspiciousOperation

from galaxy_ng.app.dynaconf_hooks import (
    post as post_hook,
    configure_cors,
    configure_logging,
    configure_socialauth,
    configure_renderers,
    configure_legacy_roles,
    configure_dynamic_settings,
    _parse_forwarded_header,
    alter_hostname_settings,
    read_settings_from_cache_or_db,
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


class TestParseForwardedHeader:
    """Test suite for the _parse_forwarded_header function."""

    def test_parse_basic_proto_and_host(self):
        """Test parsing basic proto and host parameters."""
        proto, host = _parse_forwarded_header('proto=https;host=example.com')
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_with_for_and_by_parameters(self):
        """Test parsing with additional for and by parameters."""
        proto, host = _parse_forwarded_header(
            'for=192.0.2.60;proto=http;by=203.0.113.43;host=test.com'
        )
        assert proto == 'http'
        assert host == 'test.com'

    def test_parse_quoted_values(self):
        """Test parsing quoted parameter values."""
        proto, host = _parse_forwarded_header('proto="https";host="example.com"')
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_multiple_entries_comma_separated(self):
        """Test parsing multiple forwarded entries separated by commas."""
        # First proto and host should win
        proto, host = _parse_forwarded_header(
            'for=192.0.2.60;proto=http, proto=https;host=example.com'
        )
        assert proto == 'http'  # First one wins
        assert host == 'example.com'

    def test_parse_missing_proto(self):
        """Test parsing when proto is missing."""
        proto, host = _parse_forwarded_header('host=example.com')
        assert proto is None
        assert host == 'example.com'

    def test_parse_missing_host(self):
        """Test parsing when host is missing."""
        proto, host = _parse_forwarded_header('proto=https')
        assert proto == 'https'
        assert host is None

    def test_parse_empty_header(self):
        """Test parsing empty header."""
        proto, host = _parse_forwarded_header('')
        assert proto is None
        assert host is None

    def test_parse_complex_header_with_multiple_params(self):
        """Test parsing complex header with multiple parameters."""
        header = 'for=192.0.2.60;proto=https;by=203.0.113.43;host=api.example.com'
        proto, host = _parse_forwarded_header(header)
        assert proto == 'https'
        assert host == 'api.example.com'

    def test_parse_header_with_spaces(self):
        """Test parsing header with extra spaces."""
        header = ' proto = https ; host = example.com '
        proto, host = _parse_forwarded_header(header)
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_case_insensitive_parameters(self):
        """Test that parameter names are case insensitive."""
        proto, host = _parse_forwarded_header('Proto=https;Host=example.com')
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_mixed_quoted_and_unquoted(self):
        """Test parsing mix of quoted and unquoted values."""
        proto, host = _parse_forwarded_header('proto="https";host=example.com')
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_header_with_irrelevant_parameters(self):
        """Test parsing header with parameters we don't care about."""
        header = 'for=192.0.2.60;proto=https;by=203.0.113.43;host=example.com;unknown=value'
        proto, host = _parse_forwarded_header(header)
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_malformed_parameter_no_equals(self):
        """Test parsing with malformed parameters (no equals sign)."""
        # Should gracefully handle malformed params and still parse valid ones
        proto, host = _parse_forwarded_header('malformed;proto=https;host=example.com')
        assert proto == 'https'
        assert host == 'example.com'

    def test_parse_first_value_wins_for_duplicates(self):
        """Test that first value wins when parameters are duplicated."""
        proto, host = _parse_forwarded_header(
            'proto=https;proto=http;host=first.com;host=second.com'
        )
        assert proto == 'https'  # First proto wins
        assert host == 'first.com'  # First host wins

    def test_parse_complex_real_world_example(self):
        """Test parsing a complex real-world example."""
        header = 'for=203.0.113.195;proto=https;by=203.0.113.43;host=api.galaxy.com'
        proto, host = _parse_forwarded_header(header)
        assert proto == 'https'
        assert host == 'api.galaxy.com'


class TestAlterHostnameSettings:
    """Test suite for the alter_hostname_settings function."""

    def _create_mock_value(self, value="original_value"):
        """Helper to create a mock HookValue object."""
        mock_value = Mock()
        mock_value.value = value
        return mock_value

    def _create_mock_request(self, headers=None, is_secure=False):
        """Helper to create a mock request object."""
        mock_request = Mock()
        mock_request.headers = headers or {}
        mock_request.is_secure.return_value = is_secure
        return mock_request

    def _create_mock_settings(self, is_connected=False):
        """Helper to create a mock settings object."""
        mock_settings = Mock()
        mock_settings.get.side_effect = lambda key, default=None: {
            "IS_CONNECTED_TO_RESOURCE_SERVER": is_connected
        }.get(key, default)
        return mock_settings

    # Tests for early return conditions

    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_value_when_apps_not_ready(self, mock_apps):
        """Test that original value is returned when Django apps are not ready."""
        mock_apps.ready = False
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "original_value"

    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_value_for_non_allowed_key(self, mock_apps):
        """Test that original value is returned for keys not in ALLOWED_KEYS."""
        mock_apps.ready = True
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "SOME_OTHER_KEY")

        assert result == "original_value"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_value_when_no_request_context(
        self, mock_apps, mock_get_request
    ):
        """Test that original value is returned when no request context available."""
        mock_apps.ready = True
        mock_get_request.return_value = None
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "original_value"

    # Tests for allowed keys

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_accepts_content_origin_key(self, mock_apps, mock_get_request):
        """Test that CONTENT_ORIGIN is an allowed key."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_accepts_ansible_api_hostname_key(self, mock_apps, mock_get_request):
        """Test that ANSIBLE_API_HOSTNAME is an allowed key."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "api.example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "ANSIBLE_API_HOSTNAME")

        assert result == "https://api.example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_accepts_token_server_key_and_appends_path(self, mock_apps, mock_get_request):
        """Test that TOKEN_SERVER is an allowed key and /token/ path is appended."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "auth.example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "TOKEN_SERVER")

        assert result == "https://auth.example.com/token/"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_key_is_case_insensitive(self, mock_apps, mock_get_request):
        """Test that key matching is case insensitive."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"X-Forwarded-Proto": "https", "X-Forwarded-Host": "example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "content_origin")

        assert result == "https://example.com"

    # Tests for X-Forwarded-* headers

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_uses_x_forwarded_proto_header(self, mock_apps, mock_get_request):
        """Test that X-Forwarded-Proto header is used for protocol."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "example.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_uses_x_forwarded_host_header(self, mock_apps, mock_get_request):
        """Test that X-Forwarded-Host header is preferred for host."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "forwarded.example.com",
                "Host": "original.example.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://forwarded.example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_falls_back_to_host_header_when_no_x_forwarded_host(
        self, mock_apps, mock_get_request
    ):
        """Test fallback to Host header when X-Forwarded-Host is not present."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "Host": "host.example.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://host.example.com"

    # Tests for RFC 7239 Forwarded header fallback

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_uses_rfc7239_forwarded_header_when_no_x_forwarded(
        self, mock_apps, mock_get_request
    ):
        """Test that RFC 7239 Forwarded header is used as fallback."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"Forwarded": "proto=https;host=forwarded.example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://forwarded.example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_uses_forwarded_proto_when_x_forwarded_proto_missing(
        self, mock_apps, mock_get_request
    ):
        """Test that Forwarded proto is used when X-Forwarded-Proto is missing."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Host": "example.com",
                "Forwarded": "proto=https"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_uses_forwarded_host_when_x_forwarded_host_and_host_missing(
        self, mock_apps, mock_get_request
    ):
        """Test that Forwarded host is used when X-Forwarded-Host and Host are missing."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "Forwarded": "host=forwarded.example.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://forwarded.example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_x_forwarded_takes_precedence_over_forwarded(self, mock_apps, mock_get_request):
        """Test that X-Forwarded-* headers take precedence over Forwarded header."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "x-forwarded.example.com",
                "Forwarded": "proto=http;host=forwarded.example.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://x-forwarded.example.com"

    # Tests for resource server connected mode (strict validation)

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_raises_error_when_resource_server_connected_and_no_proto(
        self, mock_apps, mock_get_request
    ):
        """Test that error is raised when connected to resource server without proto."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"Host": "example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings(is_connected=True)

        with pytest.raises(SuspiciousOperation) as exc_info:
            alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert "proto and host must be provided" in str(exc_info.value)
        assert "proto='None'" in str(exc_info.value)

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_raises_error_when_resource_server_connected_and_no_host(
        self, mock_apps, mock_get_request
    ):
        """Test that error is raised when connected to resource server without host."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"X-Forwarded-Proto": "https"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings(is_connected=True)

        with pytest.raises(SuspiciousOperation) as exc_info:
            alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert "proto and host must be provided" in str(exc_info.value)
        assert "host='None'" in str(exc_info.value)

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_raises_error_when_resource_server_connected_and_no_headers(
        self, mock_apps, mock_get_request
    ):
        """Test that error is raised when connected to resource server without any headers."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(headers={})
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings(is_connected=True)

        with pytest.raises(SuspiciousOperation) as exc_info:
            alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert "When connected to resource server" in str(exc_info.value)

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_works_when_resource_server_connected_with_valid_headers(
        self, mock_apps, mock_get_request
    ):
        """Test successful operation when connected to resource server with valid headers."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "secure.example.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings(is_connected=True)

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://secure.example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_works_when_resource_server_connected_with_forwarded_header(
        self, mock_apps, mock_get_request
    ):
        """Test successful operation when connected to resource server with Forwarded header."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"Forwarded": "proto=https;host=secure.example.com"}
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings(is_connected=True)

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://secure.example.com"

    # Tests for fallback behavior (not connected to resource server)

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_falls_back_to_http_when_request_not_secure(self, mock_apps, mock_get_request):
        """Test fallback to http when no proto header and request is not secure."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"Host": "example.com"},
            is_secure=False
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "http://example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_falls_back_to_https_when_request_is_secure(self, mock_apps, mock_get_request):
        """Test fallback to https when no proto header and request is secure."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"Host": "example.com"},
            is_secure=True
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_falls_back_to_localhost_when_no_host_headers(self, mock_apps, mock_get_request):
        """Test fallback to localhost:5001 when no host headers present."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={"X-Forwarded-Proto": "https"},
            is_secure=True
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://localhost:5001"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_full_fallback_to_defaults(self, mock_apps, mock_get_request):
        """Test full fallback when no relevant headers are present."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(headers={}, is_secure=False)
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "http://localhost:5001"

    # Tests for complex/real-world scenarios

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_real_world_reverse_proxy_scenario(self, mock_apps, mock_get_request):
        """Test a realistic reverse proxy scenario."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "hub.ansible.com",
                "X-Forwarded-For": "192.168.1.100",
                "Host": "internal-hub.local:8080"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://hub.ansible.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_complex_forwarded_header_with_multiple_proxies(
        self, mock_apps, mock_get_request
    ):
        """Test RFC 7239 Forwarded header with multiple proxy entries."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "Forwarded": (
                    'for=192.0.2.60;proto=https;host=external.example.com, '
                    'for=10.0.0.1;proto=http;host=internal.example.com'
                )
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        # First entry should win
        assert result == "https://external.example.com"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_token_server_with_complex_headers(self, mock_apps, mock_get_request):
        """Test TOKEN_SERVER key with complex forwarding headers."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "auth.ansible.com"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "TOKEN_SERVER")

        assert result == "https://auth.ansible.com/token/"

    @patch('galaxy_ng.app.dynaconf_hooks.get_current_request')
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_host_with_port_preserved(self, mock_apps, mock_get_request):
        """Test that port numbers in host are preserved."""
        mock_apps.ready = True
        mock_request = self._create_mock_request(
            headers={
                "X-Forwarded-Proto": "https",
                "X-Forwarded-Host": "example.com:8443"
            }
        )
        mock_get_request.return_value = mock_request
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = alter_hostname_settings(mock_settings, mock_value, "CONTENT_ORIGIN")

        assert result == "https://example.com:8443"


class TestReadSettingsFromCacheOrDb:
    """Test suite for the read_settings_from_cache_or_db function."""

    def _create_mock_value(self, value="original_value"):
        """Helper to create a mock HookValue object."""
        mock_value = Mock()
        mock_value.value = value
        return mock_value

    def _create_mock_settings(self, get_return_value=None):
        """Helper to create a mock settings object."""
        mock_settings = Mock()
        if get_return_value is not None:
            mock_settings.get.return_value = get_return_value
        else:
            mock_settings.get.side_effect = lambda key, default=None: default
        return mock_settings

    # Tests for early return conditions

    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_value_when_apps_not_ready(self, mock_apps):
        """Test that original value is returned when Django apps are not ready."""
        mock_apps.ready = False
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        result = read_settings_from_cache_or_db(mock_settings, mock_value, "SOME_KEY")

        assert result == "original_value"

    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_value_for_key_not_in_schema(self, mock_apps):
        """Test that original value is returned for keys not in DYNAMIC_SETTINGS_SCHEMA."""
        mock_apps.ready = True
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        # Use a key that's definitely not in the schema
        result = read_settings_from_cache_or_db(
            mock_settings, mock_value, "NOT_A_DYNAMIC_SETTING_KEY_XYZ"
        )

        assert result == "original_value"

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_value_when_dynaconf_import_fails(self, mock_apps):
        """Test graceful degradation when dynaconf imports fail."""
        mock_apps.ready = True
        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()

        # Simulate ImportError by patching the import
        with (
            patch.dict('sys.modules', {'dynaconf': None}),
            patch('builtins.__import__', side_effect=ImportError("test"))
        ):
            result = read_settings_from_cache_or_db(
                mock_settings, mock_value, "TEST_KEY"
            )

        assert result == "original_value"

    # Tests for cache/db loading behavior
    # Note: These tests use patch on the module where the import is resolved from.
    # The function does lazy imports, so we patch the source module.

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_loads_settings_from_cache_first(self, mock_apps):
        """Test that cache is checked before database."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"TEST_KEY": "cached_value"})
        mock_get_db = Mock(return_value={"TEST_KEY": "db_value"})

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        # Clear side_effect and set return_value for get()
        mock_settings.get.side_effect = None
        mock_settings.get.return_value = "cached_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            result = read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        mock_get_cache.assert_called_once()
        mock_get_db.assert_not_called()
        assert result == "cached_value"

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_falls_back_to_db_when_cache_empty(self, mock_apps):
        """Test that database is checked when cache is empty."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value=None)
        mock_get_db = Mock(return_value={"TEST_KEY": "db_value"})

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        # Clear side_effect and set return_value for get()
        mock_settings.get.side_effect = None
        mock_settings.get.return_value = "db_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            result = read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        mock_get_cache.assert_called_once()
        mock_get_db.assert_called_once()
        assert result == "db_value"

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_returns_original_when_cache_and_db_empty(self, mock_apps):
        """Test that original value is returned when both cache and db are empty."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value=None)
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value("fallback_value")
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "fallback_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            result = read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        assert result == "fallback_value"

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_updates_temp_settings_with_cached_data(self, mock_apps):
        """Test that temp_settings is updated with data from cache."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"TEST_KEY": "cached_value", "OTHER_KEY": "other"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "cached_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Verify update was called with the cached data
        mock_settings.update.assert_called_once()
        call_args = mock_settings.update.call_args
        assert call_args[0][0] == {"TEST_KEY": "cached_value", "OTHER_KEY": "other"}
        assert call_args[1]["tomlfy"] is True

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_updates_temp_settings_with_db_data(self, mock_apps):
        """Test that temp_settings is updated with data from database."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value=None)
        mock_get_db = Mock(return_value={"TEST_KEY": "db_value"})

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "db_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Verify update was called with the db data
        mock_settings.update.assert_called_once()
        call_args = mock_settings.update.call_args
        assert call_args[0][0] == {"TEST_KEY": "db_value"}
        assert call_args[1]["tomlfy"] is True

    # Tests for error handling

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_handles_dynaconf_format_error(self, mock_apps, mock_logger):
        """Test that DynaconfFormatError is caught and logged."""
        from dynaconf import DynaconfFormatError

        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"TEST_KEY": "bad_value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value("fallback")
        mock_settings = self._create_mock_settings()
        mock_settings.update.side_effect = DynaconfFormatError("Format error")
        mock_settings.get.return_value = "fallback"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            result = read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        mock_logger.error.assert_called()
        assert "Format error" in str(mock_logger.error.call_args)
        assert result == "fallback"

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_handles_dynaconf_parse_error(self, mock_apps, mock_logger):
        """Test that DynaconfParseError is caught and logged."""
        from dynaconf import DynaconfParseError

        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"TEST_KEY": "bad_value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value("fallback")
        mock_settings = self._create_mock_settings()
        mock_settings.update.side_effect = DynaconfParseError("Parse error")
        mock_settings.get.return_value = "fallback"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            result = read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        mock_logger.error.assert_called()
        assert "Parse error" in str(mock_logger.error.call_args)
        assert result == "fallback"

    # Tests for logging behavior

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_logs_debug_when_settings_empty(self, mock_apps, mock_logger):
        """Test that debug message is logged when no dynamic settings found."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value=None)
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "original_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Check that debug was called with message about empty settings
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("empty" in call.lower() for call in debug_calls)

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_logs_debug_when_key_loaded_from_cache(self, mock_apps, mock_logger):
        """Test that debug message is logged when key is loaded from cache."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"TEST_KEY": "cached_value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "cached_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Check that debug was called with cache identifier
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("cache" in call.lower() for call in debug_calls)

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_logs_debug_when_key_loaded_from_db(self, mock_apps, mock_logger):
        """Test that debug message is logged when key is loaded from database."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value=None)
        mock_get_db = Mock(return_value={"TEST_KEY": "db_value"})

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "db_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Check that debug was called with db identifier
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("db" in call.lower() for call in debug_calls)

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_logs_debug_when_key_not_in_data(self, mock_apps, mock_logger):
        """Test that debug message is logged when key is not in the loaded data."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"OTHER_KEY": "other_value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value("original")
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "original"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Check that debug was called mentioning the key is not in db/cache
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        assert any("not on db/cache" in call.lower() for call in debug_calls)

    # Tests for key matching with nested keys

    @patch('galaxy_ng.app.dynaconf_hooks.logger')
    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"PARENT": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_matches_parent_key_from_nested_data(self, mock_apps, mock_logger):
        """Test that parent key is matched when data contains nested keys."""
        mock_apps.ready = True

        # Data contains nested key like PARENT__CHILD
        mock_get_cache = Mock(return_value={"PARENT__CHILD": "nested_value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "nested_value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "PARENT")

        # Should log that key was loaded (not that it's missing)
        debug_calls = [str(call) for call in mock_logger.debug.call_args_list]
        # The key PARENT should be found because PARENT__CHILD.split("__")[0] == "PARENT"
        assert any("loaded from" in call.lower() for call in debug_calls)

    # Tests for case sensitivity

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_key_matching_is_case_insensitive_for_input(self, mock_apps):
        """Test that input key matching is case insensitive (key.upper() is used)."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"test_key": "value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        # Clear side_effect and set return_value for get()
        mock_settings.get.side_effect = None
        mock_settings.get.return_value = "value"

        # Key is lowercase but schema has uppercase - should still match due to key.upper()
        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            result = read_settings_from_cache_or_db(mock_settings, mock_value, "test_key")

        # Should have loaded from cache (not returned original)
        mock_get_cache.assert_called_once()
        assert result == "value"

    # Tests for metadata

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_metadata_identifier_is_cache_when_loaded_from_cache(self, mock_apps):
        """Test that metadata identifier is 'cache' when loaded from cache."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value={"TEST_KEY": "value"})
        mock_get_db = Mock(return_value=None)

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Check that update was called with metadata containing 'cache' identifier
        call_args = mock_settings.update.call_args
        metadata = call_args[1]["loader_identifier"]
        assert metadata.identifier == "cache"
        assert metadata.loader == "hooking"

    @patch('galaxy_ng.app.dynaconf_hooks.DYNAMIC_SETTINGS_SCHEMA', {"TEST_KEY": {}})
    @patch('galaxy_ng.app.dynaconf_hooks.apps')
    def test_metadata_identifier_is_db_when_loaded_from_db(self, mock_apps):
        """Test that metadata identifier is 'db' when loaded from database."""
        mock_apps.ready = True

        mock_get_cache = Mock(return_value=None)
        mock_get_db = Mock(return_value={"TEST_KEY": "value"})

        mock_value = self._create_mock_value()
        mock_settings = self._create_mock_settings()
        mock_settings.get.return_value = "value"

        with patch.dict('sys.modules', {
            'galaxy_ng.app.tasks.settings_cache': Mock(
                get_settings_from_cache=mock_get_cache,
                get_settings_from_db=mock_get_db
            )
        }):
            read_settings_from_cache_or_db(mock_settings, mock_value, "TEST_KEY")

        # Check that update was called with metadata containing 'db' identifier
        call_args = mock_settings.update.call_args
        metadata = call_args[1]["loader_identifier"]
        assert metadata.identifier == "db"
        assert metadata.loader == "hooking"
