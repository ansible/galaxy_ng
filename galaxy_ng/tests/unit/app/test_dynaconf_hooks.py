import copy
import pytest

from galaxy_ng.app.dynaconf_hooks import post as post_hook
from galaxy_ng.app.dynaconf_hooks import configure_keycloak


class SuperDict(dict):

    immutable = False

    def set(self, key, value):
        if self.immutable:
            raise Exception("not mutable!")
        self[key] = value

    def get(self, key, default=None):
        return self[key] if key in self else default

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
}

BASE_KEYCLOAK_SETTINGS = {
    "BASE_DIR": "templates",
    "SOCIAL_AUTH_KEYCLOAK_KEY": "key123",
    "SOCIAL_AUTH_KEYCLOAK_SECRET": "secret123",
    "SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY": "pubkey123",
    "KEYCLOAK_HOST": "mykeycloak",
    "KEYCLOAK_PORT": 1337,
    "KEYCLOAK_REALM": "aap",
}


@pytest.mark.parametrize(
    "do_stuff, extra_settings, expected_results",
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
                    "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
                ],
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
                ],
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
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
                    "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "GALAXY_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
                    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
                    "rest_framework.authentication.TokenAuthentication",
                    "rest_framework.authentication.BasicAuthentication",
                ],
                "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": [
                    "galaxy_ng.app.auth.session.SessionAuthentication",
                    "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth",
                    "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
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
    do_stuff, extra_settings, expected_results
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


@pytest.mark.parametrize(
    "do_stuff, extra_settings, expected_results",
    [
        (
            True,
            {},
            {
                "INSTALLED_APPS": ["social_django", "dynaconf_merge_unique"],
                "KEYCLOAK_URL": "https://mykeycloak:1337",
                "SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL":
                    "https://mykeycloak:1337/realms/aap/protocol/openid-connect/auth/",
                "SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL":
                    "https://mykeycloak:1337/realms/aap/protocol/openid-connect/token/",
                "GALAXY_AUTH_KEYCLOAK_ENABLED": True,
                "GALAXY_FEATURE_FLAGS__external_authentication": True,
                "GALAXY_TOKEN_EXPIRATION": 1440,
            },
        ),
        (
            True,
            {
                "KEYCLOAK_AUTH_PREFIX": "auth/",
                "KEYCLOAK_PROTOCOL": "http",
                "GALAXY_TOKEN_EXPIRATION": 0,
            },
            {
                "INSTALLED_APPS": ["social_django", "dynaconf_merge_unique"],
                "KEYCLOAK_URL": "http://mykeycloak:1337",
                "SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL":
                    "http://mykeycloak:1337/auth/realms/aap/protocol/openid-connect/auth/",
                "SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL":
                    "http://mykeycloak:1337/auth/realms/aap/protocol/openid-connect/token/",
                "GALAXY_AUTH_KEYCLOAK_ENABLED": True,
                "GALAXY_FEATURE_FLAGS__external_authentication": True,
                "GALAXY_TOKEN_EXPIRATION": 0,
            },
        ),
        (
            True,
            {
                "SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL":
                    "httpZ://mykeycloAk:1339/auth__/realms/aap/protocol/openid-connect/auth/",
                "SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL":
                    "httpZ://mykeycloAk:1339/auth__/realms/aap/protocol/openid-connect/token/",
            },
            {
                "SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL":
                    "httpZ://mykeycloAk:1339/auth__/realms/aap/protocol/openid-connect/auth/",
                "SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL":
                    "httpZ://mykeycloAk:1339/auth__/realms/aap/protocol/openid-connect/token/",
            },
        ),

    ],
)
def test_dynaconf_hook_configure_keycloak(do_stuff, extra_settings, expected_results):
    # skip test this way ...
    if not do_stuff:
        return

    xsettings = SuperDict()
    xsettings.update(copy.deepcopy(BASE_KEYCLOAK_SETTINGS))
    if extra_settings:
        xsettings.update(copy.deepcopy(extra_settings))

    # don't allow the downstream to edit this data ...
    xsettings.immutable = True

    # run the function and get the result ...
    new_settings = configure_keycloak(xsettings)

    for key, val in expected_results.items():
        assert new_settings.get(key) == val
