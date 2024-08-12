"""
This file defines a post load hook for dynaconf,
After loading all the settings files from all enabled Pulp plugins and envvars,
dynaconf will call a function named `post` and if that function returns a
dictionary containing {key:value} those values will be added, or merged to
the previously loaded settings.

This file exists to enable conditionally loaded settings variables, variables
that depends on other variable state and then requires the final state of the
settings before making conditionals.

Read more: https://www.dynaconf.com/advanced/#hooks
"""
import json
import logging
import os
import re
from typing import Any, Dict, List

import ldap
import pkg_resources
from ansible_base.lib.dynamic_config.settings_logic import get_dab_settings
from crum import get_current_request
from django.apps import apps
from django_auth_ldap.config import LDAPSearch
from dynaconf import Dynaconf, Validator

from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA

logger = logging.getLogger(__name__)


def post(settings: Dynaconf) -> Dict[str, Any]:
    """The dynaconf post hook is called after all the settings are loaded and set.

    Post hook is necessary when a setting key depends conditionally on a previouslys et variable.

    settings: A read-only copy of the django.conf.settings
    returns: a dictionary to be merged to django.conf.settings

    NOTES:
        Feature flags must be loaded directly on `app/api/ui/views/feature_flags.py` view.
    """
    data = {"dynaconf_merge": False}
    # existing keys will be merged if dynaconf_merge is set to True
    # here it is set to false, so it allows each value to be individually marked as a merge.

    data.update(configure_ldap(settings))
    data.update(configure_logging(settings))
    data.update(configure_keycloak(settings))
    data.update(configure_socialauth(settings))
    data.update(configure_cors(settings))
    data.update(configure_pulp_ansible(settings))
    data.update(configure_authentication_backends(settings))
    data.update(configure_renderers(settings))
    data.update(configure_password_validators(settings))
    data.update(configure_api_base_path(settings))
    data.update(configure_legacy_roles(settings))
    data.update(configure_dab_required_settings(settings))

    # This should go last, and it needs to receive the data from the previous configuration
    # functions because this function configures the rest framework auth classes based off
    # of the galaxy auth classes, and if galaxy auth classes are overridden by any of the
    # other dynaconf hooks (such as keycloak), those changes need to be applied to the
    # rest framework auth classes too.
    data.update(configure_authentication_classes(settings, data))

    # This must go last, so that all the default settings are loaded before dynamic and validation
    data.update(configure_dynamic_settings(settings))

    validate(settings)
    return data


def configure_keycloak(settings: Dynaconf) -> Dict[str, Any]:
    """Configure keycloak settings for galaxy.

    This function returns a dictionary that will be merged to the settings.
    """

    data = {}

    # Obtain values for Social Auth
    SOCIAL_AUTH_KEYCLOAK_KEY = settings.get("SOCIAL_AUTH_KEYCLOAK_KEY", default=None)
    SOCIAL_AUTH_KEYCLOAK_SECRET = settings.get("SOCIAL_AUTH_KEYCLOAK_SECRET", default=None)
    SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = settings.get("SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY", default=None)
    KEYCLOAK_PROTOCOL = settings.get("KEYCLOAK_PROTOCOL", default=None)
    KEYCLOAK_HOST = settings.get("KEYCLOAK_HOST", default=None)
    KEYCLOAK_PORT = settings.get("KEYCLOAK_PORT", default=None)
    KEYCLOAK_REALM = settings.get("KEYCLOAK_REALM", default=None)

    # Add settings if Social Auth values are provided
    if all(
        [
            SOCIAL_AUTH_KEYCLOAK_KEY,
            SOCIAL_AUTH_KEYCLOAK_SECRET,
            SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY,
            KEYCLOAK_HOST,
            KEYCLOAK_PORT,
            KEYCLOAK_REALM,
        ]
    ):
        data["KEYCLOAK_ADMIN_ROLE"] = settings.get("KEYCLOAK_ADMIN_ROLE", default="hubadmin")
        data["KEYCLOAK_GROUP_TOKEN_CLAIM"] = settings.get(
            "KEYCLOAK_GROUP_TOKEN_CLAIM", default="group"
        )
        data["KEYCLOAK_ROLE_TOKEN_CLAIM"] = settings.get(
            "KEYCLOAK_GROUP_TOKEN_CLAIM", default="client_roles"
        )
        data["KEYCLOAK_HOST_LOOPBACK"] = settings.get("KEYCLOAK_HOST_LOOPBACK", default=None)
        data["KEYCLOAK_URL"] = f"{KEYCLOAK_PROTOCOL}://{KEYCLOAK_HOST}:{KEYCLOAK_PORT}"
        auth_url_str = "{keycloak}/auth/realms/{realm}/protocol/openid-connect/auth/"
        data["SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL"] = auth_url_str.format(
            keycloak=data["KEYCLOAK_URL"], realm=KEYCLOAK_REALM
        )
        if data["KEYCLOAK_HOST_LOOPBACK"]:
            loopback_url = "{protocol}://{host}:{port}".format(
                protocol=KEYCLOAK_PROTOCOL, host=data["KEYCLOAK_HOST_LOOPBACK"], port=KEYCLOAK_PORT
            )
            data["SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL"] = auth_url_str.format(
                keycloak=loopback_url, realm=KEYCLOAK_REALM
            )

        data[
            "SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL"
        ] = f"{data['KEYCLOAK_URL']}/auth/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/"

        data["SOCIAL_AUTH_LOGIN_REDIRECT_URL"] = settings.get(
            "SOCIAL_AUTH_LOGIN_REDIRECT_URL", default="/ui/"
        )
        data["SOCIAL_AUTH_JSONFIELD_ENABLED"] = True
        # data["SOCIAL_AUTH_JSONFIELD_CUSTOM"] = "django.db.models.JSONField"
        data["SOCIAL_AUTH_URL_NAMESPACE"] = "social"
        data["SOCIAL_AUTH_KEYCLOAK_EXTRA_DATA"] = [
            ("refresh_token", "refresh_token"),
            (data["KEYCLOAK_ROLE_TOKEN_CLAIM"], data["KEYCLOAK_ROLE_TOKEN_CLAIM"]),
        ]

        data["SOCIAL_AUTH_PIPELINE"] = (
            "social_core.pipeline.social_auth.social_details",
            "social_core.pipeline.social_auth.social_uid",
            "social_core.pipeline.social_auth.social_user",
            "social_core.pipeline.user.get_username",
            "social_core.pipeline.social_auth.associate_by_email",
            "social_core.pipeline.user.create_user",
            "social_core.pipeline.social_auth.associate_user",
            "social_core.pipeline.social_auth.load_extra_data",
            "social_core.pipeline.user.user_details",
            "galaxy_ng.app.pipelines.user_role",
            "galaxy_ng.app.pipelines.user_group",
        )

        # Set external authentication feature flag
        # data["GALAXY_FEATURE_FLAGS"] = {'external_authentication': True, "dynaconf_merge": True}
        # The next have the same effect ^
        data["GALAXY_FEATURE_FLAGS__external_authentication"] = True

        # Add to installed apps
        data["INSTALLED_APPS"] = ["social_django", "dynaconf_merge_unique"]

        # Add to authentication backends
        data["AUTHENTICATION_BACKENDS"] = [
            "social_core.backends.keycloak.KeycloakOAuth2",
            "dynaconf_merge",
        ]

        # Replace AUTH CLASSES
        data["GALAXY_AUTHENTICATION_CLASSES"] = [
            "galaxy_ng.app.auth.session.SessionAuthentication",
            "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
            "galaxy_ng.app.auth.keycloak.KeycloakBasicAuth"
        ]

        # Set default to one day expiration
        data["GALAXY_TOKEN_EXPIRATION"] = settings.get("GALAXY_TOKEN_EXPIRATION", 1440)

        # Add to templates
        # Pending dynaconf issue:
        # https://github.com/rochacbruno/dynaconf/issues/299#issuecomment-900616706
        # So we can do a merge of this data.
        data["TEMPLATES"] = [
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
                "DIRS": [os.path.join(settings.BASE_DIR, "templates")],
                "APP_DIRS": True,
                "OPTIONS": {
                    "context_processors": [
                        # BEGIN: Pulp standard context processors
                        "django.template.context_processors.debug",
                        "django.template.context_processors.request",
                        "django.contrib.auth.context_processors.auth",
                        "django.contrib.messages.context_processors.messages",
                        # END: Pulp standard context processors
                        "social_django.context_processors.backends",
                        "social_django.context_processors.login_redirect",
                    ],
                },
            },
        ]

    return data


def configure_socialauth(settings: Dynaconf) -> Dict[str, Any]:
    """Configure social auth settings for galaxy.

    This function returns a dictionary that will be merged to the settings.
    """

    data = {}

    # SOCIAL_AUTH_GITHUB_BASE_URL = \
    #   settings.get('SOCIAL_AUTH_GITHUB_BASE_URL', default='https://github.com')
    # SOCIAL_AUTH_GITHUB_API_URL = \
    #   settings.get('SOCIAL_AUTH_GITHUB_BASE_URL', default='https://api.github.com')

    SOCIAL_AUTH_GITHUB_KEY = settings.get("SOCIAL_AUTH_GITHUB_KEY", default=None)
    SOCIAL_AUTH_GITHUB_SECRET = settings.get("SOCIAL_AUTH_GITHUB_SECRET", default=None)

    if all([SOCIAL_AUTH_GITHUB_KEY, SOCIAL_AUTH_GITHUB_SECRET]):

        # Add to installed apps
        data["INSTALLED_APPS"] = ["social_django", "dynaconf_merge_unique"]

        # Make sure the UI knows to do ext auth
        data["GALAXY_FEATURE_FLAGS__external_authentication"] = True

        backends = settings.get("AUTHENTICATION_BACKENDS", default=[])
        backends.append("galaxy_ng.social.GalaxyNGOAuth2")
        backends.append("dynaconf_merge")
        data["AUTHENTICATION_BACKENDS"] = backends
        data["DEFAULT_AUTHENTICATION_BACKENDS"] = backends
        data["GALAXY_AUTHENTICATION_BACKENDS"] = backends

        data['DEFAULT_AUTHENTICATION_CLASSES'] = [
            "galaxy_ng.app.auth.session.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ]

        data['GALAXY_AUTHENTICATION_CLASSES'] = [
            "galaxy_ng.app.auth.session.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ]

        data['REST_FRAMEWORK_AUTHENTICATION_CLASSES'] = [
            "galaxy_ng.app.auth.session.SessionAuthentication",
            "rest_framework.authentication.TokenAuthentication",
            "rest_framework.authentication.BasicAuthentication",
        ]

        # Override the get_username and create_user steps
        # to conform to our super special user validation
        # requirements
        data['SOCIAL_AUTH_PIPELINE'] = [
            'social_core.pipeline.social_auth.social_details',
            'social_core.pipeline.social_auth.social_uid',
            'social_core.pipeline.social_auth.auth_allowed',
            'social_core.pipeline.social_auth.social_user',
            'galaxy_ng.social.pipeline.user.get_username',
            'galaxy_ng.social.pipeline.user.create_user',
            'social_core.pipeline.social_auth.associate_user',
            'social_core.pipeline.social_auth.load_extra_data',
            'social_core.pipeline.user.user_details'
        ]

    return data


def configure_logging(settings: Dynaconf) -> Dict[str, Any]:
    data = {
        "GALAXY_ENABLE_API_ACCESS_LOG": settings.get(
            "GALAXY_ENABLE_API_ACCESS_LOG",
            default=os.getenv("GALAXY_ENABLE_API_ACCESS_LOG", default=False),
        )
    }
    if data["GALAXY_ENABLE_API_ACCESS_LOG"]:
        data["INSTALLED_APPS"] = ["galaxy_ng._vendor.automated_logging", "dynaconf_merge_unique"]
        data["MIDDLEWARE"] = [
            "automated_logging.middleware.AutomatedLoggingMiddleware",
            "dynaconf_merge",
        ]
        data["LOGGING"] = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "automated_logging": {"format": "%(asctime)s: %(levelname)s: %(message)s"},
            },
            "handlers": {
                "automated_logging": {
                    "level": "INFO",
                    "class": "logging.handlers.WatchedFileHandler",
                    "filename": "/var/log/galaxy_api_access.log",
                    "formatter": "automated_logging",
                },
            },
            "loggers": {
                "automated_logging": {
                    "handlers": ["automated_logging"],
                    "level": "INFO",
                    "propagate": False,
                },
            },
            "dynaconf_merge": True,
        }
        data["AUTOMATED_LOGGING"] = {
            "globals": {
                "exclude": {
                    "applications": [
                        "plain:contenttypes",
                        "plain:admin",
                        "plain:basehttp",
                        "glob:session*",
                        "plain:migrations",
                    ]
                }
            },
            "model": {
                "detailed_message": True,
                "exclude": {"applications": [], "fields": [], "models": [], "unknown": False},
                "loglevel": 20,
                "mask": [],
                "max_age": None,
                "performance": False,
                "snapshot": False,
                "user_mirror": False,
            },
            "modules": ["request", "unspecified", "model"],
            "request": {
                "data": {
                    "content_types": ["application/json"],
                    "enabled": [],
                    "ignore": [],
                    "mask": [
                        "ca_cert",
                        "client_cert",
                        "client_key",
                        "email",
                        "password",
                        "proxy_url",
                        "proxy_username",
                        "proxy_password",
                        "token",
                        "username",
                    ],
                    "query": True,
                },
                "exclude": {
                    "applications": [],
                    "methods": [],
                    "status": [],
                    "unknown": False,
                },
                "ip": True,
                "loglevel": 20,
                "max_age": None,
            },
            "unspecified": {
                "exclude": {"applications": [], "files": [], "unknown": False},
                "loglevel": 20,
                "max_age": None,
            },
        }

    return data


def configure_cors(settings: Dynaconf) -> Dict[str, Any]:
    """This adds CORS Middleware, useful to access swagger UI on dev environment"""

    if os.getenv("DEV_SOURCE_PATH", None) is None:
        # Only add CORS if we are in dev mode
        return {}

    data = {}
    if settings.get("GALAXY_ENABLE_CORS", default=False):
        corsmiddleware = ["galaxy_ng.app.common.openapi.AllowCorsMiddleware"]
        data["MIDDLEWARE"] = corsmiddleware + settings.get("MIDDLEWARE", [])
    return data


def configure_pulp_ansible(settings: Dynaconf) -> Dict[str, Any]:
    # Translate the galaxy default base path to the pulp ansible default base path.
    distro_path = settings.get("GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH", "published")

    return {
        # ANSIBLE_URL_NAMESPACE tells pulp_ansible to generate hrefs and redirects that
        # point to the galaxy_ng api namespace. We're forcing it to get set to our api
        # namespace here because setting it to anything else will break our api.
        "ANSIBLE_URL_NAMESPACE": "galaxy:api:v3:",
        "ANSIBLE_DEFAULT_DISTRIBUTION_PATH": distro_path
    }


def configure_authentication_classes(settings: Dynaconf, data: Dict[str, Any]) -> Dict[str, Any]:
    # GALAXY_AUTHENTICATION_CLASSES is used to configure the galaxy api authentication
    # pretty much everywhere (on prem, cloud, dev environments, CI environments etc).
    # We need to set the REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES variable so that
    # the pulp APIs use the same authentication as the galaxy APIs. Rather than setting
    # the galaxy auth classes and the DRF classes in all those environments just set the
    # default rest framework auth classes to the galaxy auth classes. Ideally we should
    # switch everything to use the default DRF auth classes, but given how many
    # environments would have to be reconfigured, this is a lot easier.
    galaxy_auth_classes = data.get(
        "GALAXY_AUTHENTICATION_CLASSES",
        settings.get("GALAXY_AUTHENTICATION_CLASSES", None)
    )
    if galaxy_auth_classes:
        return {
            "REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES": galaxy_auth_classes
        }
    else:
        return {}


def configure_password_validators(settings: Dynaconf) -> Dict[str, Any]:
    """Configure the password validators"""
    GALAXY_MINIMUM_PASSWORD_LENGTH: int = settings.get("GALAXY_MINIMUM_PASSWORD_LENGTH", 9)
    AUTH_PASSWORD_VALIDATORS: List[Dict[str, Any]] = settings.AUTH_PASSWORD_VALIDATORS
    # NOTE: Dynaconf can't add or merge on dicts inside lists.
    # So we need to traverse the list to change it until the RFC is implemented
    # https://github.com/rochacbruno/dynaconf/issues/299#issuecomment-900616706
    for dict_item in AUTH_PASSWORD_VALIDATORS:
        if dict_item["NAME"].endswith("MinimumLengthValidator"):
            dict_item["OPTIONS"]["min_length"] = int(GALAXY_MINIMUM_PASSWORD_LENGTH)
    return {"AUTH_PASSWORD_VALIDATORS": AUTH_PASSWORD_VALIDATORS}


def configure_api_base_path(settings: Dynaconf) -> Dict[str, Any]:
    """Set the pulp api root under the galaxy api root."""

    galaxy_api_root = settings.get("GALAXY_API_PATH_PREFIX")
    pulp_api_root = f"/{galaxy_api_root.strip('/')}/pulp/"
    return {"API_ROOT": pulp_api_root}


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

        connection_options = settings.get("AUTH_LDAP_CONNECTION_OPTIONS", {})
        if settings.get("GALAXY_LDAP_DISABLE_REFERRALS"):
            connection_options[ldap.OPT_REFERRALS] = 0
        data["AUTH_LDAP_CONNECTION_OPTIONS"] = connection_options

        if settings.get("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS"):
            data["AUTH_LDAP_MIRROR_GROUPS"] = True
            data["AUTH_LDAP_MIRROR_GROUPS_EXCEPT"] = None

    return data


def configure_authentication_backends(settings: Dynaconf) -> Dict[str, Any]:
    """Configure authentication backends for galaxy.
    This function returns a dictionary that will be merged to the settings.
    """
    data = {}

    choosen_preset = settings.get("AUTHENTICATION_BACKEND_PRESET")
    # If `custom` it will allow user to override and not raise Validation Error
    # If `local` it will not be set and will use the default coming from pulp

    presets = settings.get("AUTHENTICATION_BACKEND_PRESETS_DATA", {})
    if choosen_preset in presets:
        data["AUTHENTICATION_BACKENDS"] = presets[choosen_preset]

    return data


def configure_renderers(settings) -> Dict[str, Any]:
    """
        Add CustomBrowsableAPI only for community (galaxy.ansible.com, galaxy-stage, galaxy-dev)"
    """
    if re.search(
        r'galaxy(-dev|-stage)*.ansible.com', settings.get('CONTENT_ORIGIN', "")
    ):
        value = settings.get("REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES", [])
        value.append('galaxy_ng.app.renderers.CustomBrowsableAPIRenderer')
        return {"REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES": value}

    return {}


def configure_legacy_roles(settings: Dynaconf) -> Dict[str, Any]:
    """Set the feature flag for legacy roles from the setting"""
    data = {}
    legacy_roles = settings.get("GALAXY_ENABLE_LEGACY_ROLES", False)
    data["GALAXY_FEATURE_FLAGS__legacy_roles"] = legacy_roles
    return data


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


def configure_dynamic_settings(settings: Dynaconf) -> Dict[str, Any]:
    """Dynaconf 3.2.2 allows registration of hooks on methods `get` and `as_dict`

    For galaxy this enables the Dynamic Settings feature, which triggers a
    specified function after every key is accessed.

    So after the normal get process, the registered hook will be able to
    change the value before it is returned allowing reading overrides from
    database and cache.
    """
    # we expect a list of function names here, which have to be in scope of
    # locals() for this specific file
    enabled_hooks = settings.get("DYNACONF_AFTER_GET_HOOKS")
    if not enabled_hooks:
        return {}

    # Perform lazy imports here to avoid breaking when system runs with older
    # dynaconf versions
    try:
        from dynaconf import DynaconfFormatError, DynaconfParseError
        from dynaconf.base import Settings
        from dynaconf.hooking import Action, Hook, HookValue
        from dynaconf.loaders.base import SourceMetadata
    except ImportError as exc:
        # Graceful degradation for dynaconf < 3.2.3 where  method hooking is not available
        logger.error(
            "Galaxy Dynamic Settings requires Dynaconf >=3.2.3, "
            "system will work normally but dynamic settings from database will be ignored: %s",
            str(exc)
        )
        return {}

    logger.info("Enabling Dynamic Settings Feature")

    def read_settings_from_cache_or_db(
        temp_settings: Settings,
        value: HookValue,
        key: str,
        *args,
        **kwargs
    ) -> Any:
        """A function to be attached on Dynaconf Afterget hook.
        Load everything from settings cache or db, process parsing and mergings,
        returns the desired key value
        """
        if not apps.ready or key.upper() not in DYNAMIC_SETTINGS_SCHEMA:
            # If app is starting up or key is not on allowed list bypass and just return the value
            return value.value

        # lazy import because it can't happen before apps are ready
        from galaxy_ng.app.tasks.settings_cache import (
            get_settings_from_cache,
            get_settings_from_db,
        )
        if data := get_settings_from_cache():
            metadata = SourceMetadata(loader="hooking", identifier="cache")
        else:
            data = get_settings_from_db()
            if data:
                metadata = SourceMetadata(loader="hooking", identifier="db")

        # This is the main part, it will update temp_settings with data coming from settings db
        # and by calling update it will process dynaconf parsing and merging.
        try:
            if data:
                temp_settings.update(data, loader_identifier=metadata, tomlfy=True)
        except (DynaconfFormatError, DynaconfParseError) as exc:
            logger.error("Error loading dynamic settings: %s", str(exc))

        if not data:
            logger.debug("Dynamic settings are empty, reading key %s from default sources", key)
        elif key in [_k.split("__")[0] for _k in data]:
            logger.debug("Dynamic setting for key: %s loaded from %s", key, metadata.identifier)
        else:
            logger.debug(
                "Key %s not on db/cache, %s other keys loaded from %s",
                key, len(data), metadata.identifier
            )

        return temp_settings.get(key, value.value)

    def alter_hostname_settings(
        temp_settings: Settings,
        value: HookValue,
        key: str,
        *args,
        **kwargs
    ) -> Any:
        """Use the request headers to dynamically alter the content origin and api hostname.
        This is useful in scenarios where the hub is accessible directly and through a
        reverse proxy.
        """

        # we only want to modify these settings base on request headers
        ALLOWED_KEYS = ['CONTENT_ORIGIN', 'ANSIBLE_API_HOSTNAME', 'TOKEN_SERVER']

        # If app is starting up or key is not on allowed list bypass and just return the value
        if not apps.ready or key.upper() not in ALLOWED_KEYS:
            return value.value

        # we have to assume the proxy or the edge device(s) set these headers correctly
        req = get_current_request()
        if req is not None:
            headers = dict(req.headers)
            proto = headers.get("X-Forwarded-Proto", "http")
            host = headers.get("Host", "localhost:5001")
            baseurl = proto + "://" + host
            if key.upper() == 'TOKEN_SERVER':
                baseurl += '/token/'
            return baseurl

        return value.value

    # avoid scope errors by not using a list comprehension
    hook_functions = []
    for func_name in enabled_hooks:
        hook_functions.append(Hook(locals()[func_name]))

    return {
        "_registered_hooks": {
            Action.AFTER_GET: hook_functions
        }
    }


def configure_dab_required_settings(settings: Dynaconf) -> Dict[str, Any]:
    dab_settings = get_dab_settings(
        installed_apps=settings.INSTALLED_APPS + ['ansible_base.jwt_consumer'],
        rest_framework=settings.REST_FRAMEWORK,
        spectacular_settings=settings.SPECTACULAR_SETTINGS,
        authentication_backends=settings.AUTHENTICATION_BACKENDS,
        middleware=settings.MIDDLEWARE,
    )
    return {k: v for k, v in dab_settings.items() if k not in settings}
