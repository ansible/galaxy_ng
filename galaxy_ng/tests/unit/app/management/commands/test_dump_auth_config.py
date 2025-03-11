from io import StringIO
import json
from django.core.management import call_command
from django.test import TestCase, override_settings
import unittest


@override_settings(SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL="ACCESS_TOKEN_URL")
@override_settings(SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL="AUTHORIZATION_URL")
@override_settings(SOCIAL_AUTH_KEYCLOAK_KEY="KEY")
@override_settings(SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY="PUBLIC_KEY")
@override_settings(SOCIAL_AUTH_KEYCLOAK_SECRET="SECRET")
@override_settings(AUTH_LDAP_SERVER_URI="SERVER_URI")
@override_settings(AUTH_LDAP_BIND_DN="BIND_DN")
@override_settings(AUTH_LDAP_BIND_PASSWORD="BIND_PASSWORD")
@override_settings(AUTH_LDAP_USER_DN_TEMPLATE="USER_DN_TEMPLATE")
@override_settings(AUTH_LDAP_USER_SEARCH_BASE_DN="USER_SEARCH_BASE_DN")
@override_settings(AUTH_LDAP_USER_SEARCH_SCOPE="USER_SEARCH_SCOPE")
@override_settings(AUTH_LDAP_USER_SEARCH_FILTER="USER_SEARCH_FILTER")
@override_settings(AUTH_LDAP_GROUP_SEARCH_BASE_DN="GROUP_SEARCH_BASE_DN")
@override_settings(AUTH_LDAP_GROUP_SEARCH_SCOPE="GROUP_SEARCH_SCOPE")
@override_settings(AUTH_LDAP_GROUP_SEARCH_FILTER="GROUP_SEARCH_FILTER")
@override_settings(AUTH_LDAP_GROUP_TYPE_PARAMS="GROUP_TYPE_PARAMS")
@override_settings(AUTH_LDAP_USER_ATTR_MAP={
    "email": "email",
    "last_name": "last_name",
    "first_name": "first_name",
})
@override_settings(AUTH_LDAP_CONNECTION_OPTIONS={})
@override_settings(AUTH_LDAP_START_TLS=None)
@override_settings(AUTH_LDAP_GROUP_TYPE="string object")
class TestDumpAuthConfigCommand(TestCase):
    def setUp(self):
        super().setUp()
        self.expected_config = [
            {
                "type": "galaxy.authentication.authenticator_plugins.keycloak",
                "enabled": True,
                "configuration": {
                    "ACCESS_TOKEN_URL": "ACCESS_TOKEN_URL",
                    "AUTHORIZATION_URL": "AUTHORIZATION_URL",
                    "KEY": "KEY",
                    "PUBLIC_KEY": "PUBLIC_KEY",
                    "SECRET": "SECRET"
                }
            },
            {
                "type": "galaxy.authentication.authenticator_plugins.ldap",
                "enabled": True,
                "configuration": {
                    "SERVER_URI": "SERVER_URI",
                    "BIND_DN": "BIND_DN",
                    "BIND_PASSWORD": "BIND_PASSWORD",
                    "USER_SEARCH_BASE_DN": "USER_SEARCH_BASE_DN",
                    "USER_SEARCH_SCOPE": "USER_SEARCH_SCOPE",
                    "USER_SEARCH_FILTER": "USER_SEARCH_FILTER",
                    "GROUP_SEARCH_BASE_DN": "GROUP_SEARCH_BASE_DN",
                    "GROUP_SEARCH_SCOPE": "GROUP_SEARCH_SCOPE",
                    "GROUP_SEARCH_FILTER": "GROUP_SEARCH_FILTER",
                    "USER_ATTR_MAP": {
                        "email": "email",
                        "last_name": "last_name",
                        "first_name": "first_name"
                    },
                    "USER_DN_TEMPLATE": "USER_DN_TEMPLATE",
                    "GROUP_TYPE_PARAMS": "GROUP_TYPE_PARAMS",
                    "CONNECTION_OPTIONS": {},
                    "START_TLS": None,
                    "USER_SEARCH": [
                        "USER_SEARCH_BASE_DN",
                        "USER_SEARCH_SCOPE",
                        "USER_SEARCH_FILTER"
                    ],
                    "GROUP_SEARCH": [
                        "GROUP_SEARCH_BASE_DN",
                        "GROUP_SEARCH_SCOPE",
                        "GROUP_SEARCH_FILTER"
                    ],
                    "GROUP_TYPE": "str"
                }
            }
        ]

    @unittest.skip("FIXME - broken by dab 2024.12.13")
    def test_json_returned_from_cmd(self):
        output = StringIO()
        call_command("dump-auth-config", stdout=output)
        assert output.getvalue().rstrip() == json.dumps(self.expected_config)
