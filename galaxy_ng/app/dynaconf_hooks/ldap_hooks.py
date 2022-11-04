import json
import ldap
import pkg_resources
from typing import Any, Dict
from dynaconf import Dynaconf
from django_auth_ldap.config import LDAPSearch


def configure_ldap(settings: Dynaconf) -> Dict[str, Any]:
    """Configure ldap settings for galaxy.
    This function returns a dictionary that will be merged to the settings.
    """

    data = {}
    AUTH_LDAP_SERVER_URI = settings.get("AUTH_LDAP_SERVER_URI", default=None)
    AUTH_LDAP_BIND_DN = settings.get("AUTH_LDAP_BIND_DN", default=None)
    AUTH_LDAP_BIND_PASSWORD = settings.get("AUTH_LDAP_BIND_PASSWORD", default=None)
    AUTH_LDAP_USER_SEARCH_BASE_DN = settings.get("AUTH_LDAP_USER_SEARCH_BASE_DN", default=None)
    AUTH_LDAP_USER_SEARCH_SCOPE = settings.get("AUTH_LDAP_USER_SEARCH_SCOPE", default=None)
    AUTH_LDAP_USER_SEARCH_FILTER = settings.get("AUTH_LDAP_USER_SEARCH_FILTER", default=None)
    AUTH_LDAP_GROUP_SEARCH_BASE_DN = settings.get("AUTH_LDAP_GROUP_SEARCH_BASE_DN", default=None)
    AUTH_LDAP_GROUP_SEARCH_SCOPE = settings.get("AUTH_LDAP_GROUP_SEARCH_SCOPE", default=None)
    AUTH_LDAP_GROUP_SEARCH_FILTER = settings.get("AUTH_LDAP_GROUP_SEARCH_FILTER", default=None)
    AUTH_LDAP_USER_ATTR_MAP = settings.get("AUTH_LDAP_USER_ATTR_MAP", default={})

    # Add settings if LDAP Auth values are provided
    if all(
        [
            AUTH_LDAP_SERVER_URI,
            AUTH_LDAP_BIND_DN,
            AUTH_LDAP_BIND_PASSWORD,
            AUTH_LDAP_USER_SEARCH_BASE_DN,
            AUTH_LDAP_USER_SEARCH_SCOPE,
            AUTH_LDAP_USER_SEARCH_FILTER,
            AUTH_LDAP_GROUP_SEARCH_BASE_DN,
            AUTH_LDAP_GROUP_SEARCH_SCOPE,
            AUTH_LDAP_GROUP_SEARCH_FILTER,
        ]
    ):
        # The following is exposed on UI settings API to be used as a feature flag for testing.
        data["GALAXY_AUTH_LDAP_ENABLED"] = True

        global_options = settings.get("AUTH_LDAP_GLOBAL_OPTIONS", default={})

        if settings.get("GALAXY_LDAP_SELF_SIGNED_CERT"):
            global_options[ldap.OPT_X_TLS_REQUIRE_CERT] = ldap.OPT_X_TLS_NEVER

        data["AUTH_LDAP_GLOBAL_OPTIONS"] = global_options

        AUTH_LDAP_SCOPE_MAP = {
            "BASE": ldap.SCOPE_BASE,
            "ONELEVEL": ldap.SCOPE_ONELEVEL,
            "SUBTREE": ldap.SCOPE_SUBTREE,
        }

        if not settings.get("AUTH_LDAP_USER_SEARCH"):
            user_scope = AUTH_LDAP_SCOPE_MAP.get(AUTH_LDAP_USER_SEARCH_SCOPE, ldap.SCOPE_SUBTREE)
            data["AUTH_LDAP_USER_SEARCH"] = LDAPSearch(
                AUTH_LDAP_USER_SEARCH_BASE_DN,
                user_scope,
                AUTH_LDAP_USER_SEARCH_FILTER
            )

        if not settings.get("AUTH_LDAP_GROUP_SEARCH"):
            group_scope = AUTH_LDAP_SCOPE_MAP.get(AUTH_LDAP_GROUP_SEARCH_SCOPE, ldap.SCOPE_SUBTREE)
            data["AUTH_LDAP_GROUP_SEARCH"] = LDAPSearch(
                AUTH_LDAP_GROUP_SEARCH_BASE_DN,
                group_scope,
                AUTH_LDAP_GROUP_SEARCH_FILTER
            )

        # Depending on the LDAP server the following might need to be changed
        # options: https://django-auth-ldap.readthedocs.io/en/latest/groups.html#types-of-groups
        # default is set to GroupOfNamesType
        # data["AUTH_LDAP_GROUP_TYPE"] = GroupOfNamesType(name_attr="cn")
        # export PULP_AUTH_LDAP_GROUP_TYPE_CLASS="django_auth_ldap.config:GroupOfNamesType"
        if classpath := settings.get(
            "AUTH_LDAP_GROUP_TYPE_CLASS",
            default="django_auth_ldap.config:GroupOfNamesType"
        ):
            group_type_class = pkg_resources.EntryPoint.parse(
                f"__name = {classpath}"
            ).resolve()
            group_type_params = settings.get(
                "AUTH_LDAP_GROUP_TYPE_PARAMS",
                default={"name_attr": "cn"}
            )
            data["AUTH_LDAP_GROUP_TYPE"] = group_type_class(**group_type_params)

        if isinstance(AUTH_LDAP_USER_ATTR_MAP, str):
            try:
                data["AUTH_LDAP_USER_ATTR_MAP"] = json.loads(AUTH_LDAP_USER_ATTR_MAP)
            except Exception:
                data["AUTH_LDAP_USER_ATTR_MAP"] = {}

        if settings.get("GALAXY_LDAP_LOGGING"):
            data["LOGGING"] = {
                "dynaconf_merge": True,
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {"console": {"class": "logging.StreamHandler"}},
                "loggers": {"django_auth_ldap": {"level": "DEBUG", "handlers": ["console"]}},
            }

    return data
