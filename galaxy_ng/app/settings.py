"""
I know, this file looks like a Django settings file but it's not!

TL;DR:

This file is a settings fragment, which will be bundled with other settings
files from other Pulp plugins, deployment customizations through
`/etc/pulp/settings.py` and also with variables from the environment,
from database, Redis and some loaded conditionally through hooks.

Long story:

Dynaconf is the library that manages settings in the Pulp application, the way
settings are loaded is defined in `pulpcore.app.settings`, in that file some
validators are also defined, as soon as Django requests `pulpcore.app.settings`
Dynaconf will step in and using Python module hooks will deliver a Dynaconf
object instead of a regular Django settings class.

This Dynaconf class will be available in `django.conf.settings`, and since it is
completely compatible with Django LazySettings, the first time a variable is
accessed it will start the loading process, which consists of:

1. Loading the values ​​from pulpcore.app.settings.py
2. Loading the values ​​from {plugin}.app.settings for each plugin
   (including galaxy_ng, in an undefined order)
3. Loading the values ​​from /etc/pulp/settings.py and /etc/pulp/settings.local.py
4. Loading the values ​​of environment variables prefixed with `PULP_`
5. Running the hooks defined in `{plugin}/app/dynaconf_hooks.py` for each of the
   plugins and loading the values ​​returned by the hooks.
6. Loading values ​​defined in the database in the `config.Setting` model for keys
   that can be changed during runtime.
7. Deliver the `settings` to `django.conf` module on sys.modules namespace

A diagram can be visualized on: https://xmind.app/m/VPSF59/

FAQ:

- How do I know from which source a variable came from?
A: `dynaconf inspect -k KEY` on command line or `inspect_settings` function
    read more on https://www.dynaconf.com/advanced/#inspecting-history

- How do I get a value from settings during the execution of a bash script?
A: `dynaconf get KEY` will output the raw value for the key (or ret code 1)
    read more on https://www.dynaconf.com/cli/#dynaconf-get

- How do I merge value coming from other sources if  it's a data structure?
A: Use any supported merging strategy e.g:

    export PULP_DATABASES__default__ENGINE=sqlite
    export PULP_DATABASES__default="@merge ENGINE=foobar"
    export PULP_INSTALLED_APPS="@merge_unique awesome_app"
    export PULP_INSTALLED_APPS='@json ["awesome_app", "dynaconf_merge_unique"]'
    export PULP_LISTOFTHINGS___0__key=value
    read more https://www.dynaconf.com/merging/
              https://www.dynaconf.com/envvars/#type-casting-and-lazy-values

Caveats:

- In this file you cannot have conditionals based on other keys,
  e.g.: `if "x" not in INSTALLED_APPS`
  because the final state of `INSTALLED_APPS` will only be known at the end of
  the loading process, if you need conditionals use dynaconf_hooks.py.
- In this file you cannot use other settings extensions for Django, it has to be
  done the Dynaconf way.
- This file should not be imported directly (just like any Django settings)
- Only variables in uppercase are considered
- On standalone scripts DO NOT use `settings.configure()` instead use
  `settings.DYNACONF.configure()` or prefer to use management command because
  those have the full django context defined.

Cautions and tips:

- Values ​​can be merged, if you want a data structure to be open for adding keys
  and values ​​or to be joined with values ​​coming from other sources, use
  `dynaconf_merge` or `dynaconf_merge_unique` (examples in the file)
- Validators can be defined in dynaconf_hooks.py
- Use settings.get(key) as the django.conf.settings will be a dict like obj
- dot notation also works for data structures
  `settings.get('databases.default.engine')`

Read more on: https://www.dynaconf.com/django/
"""

import os

DEBUG = False

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    # BEGIN: Pulp standard middleware
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django_guid.middleware.guid_middleware',
    'pulpcore.middleware.DomainMiddleware',
    # END: Pulp standard middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
MIDDLEWARE += ('crum.CurrentRequestUserMiddleware',)

INSTALLED_APPS = [
    'rest_framework.authtoken',
    'crum',
    'ansible_base.resource_registry',
    'ansible_base.rbac',
    'social_django',
    'dynaconf_merge_unique',
]

LOGGING = {
    "loggers": {
        "galaxy_ng.app.api.v1.tasks.legacy_role_import": {
            "level": "INFO",
            "handlers": ["legacyrole_import"],
            "propagate": False,
        }
    },
    "handlers": {
        "legacyrole_import": {
            "level": "DEBUG",
            "class": "galaxy_ng.app.api.v1.logutils.LegacyRoleImportHandler",
            "formatter": "simple",
        }
    },
    "dynaconf_merge": True,
}


AUTH_USER_MODEL = 'galaxy.User'

# FIXME(cutwater): 1. Rename GALAXY_API_ROOT in pulp-ansible to ANSIBLE_API_ROOT
#                  2. Rename API_PATH_PREFIX to GALAXY_API_ROOT
GALAXY_API_PATH_PREFIX = "/api/galaxy"
STATIC_URL = "/static/"

# A client connection to /api/automation-hub/ is the same as a client connection
# to /api/automation-hub/content/<GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH>/
# with the exception of galaxy_ng.app.api.v3.viewsets.CollectionUploadViewSet
GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH = "published"

GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH = "staging"
GALAXY_API_REJECTED_DISTRIBUTION_BASE_PATH = "rejected"

# The format for the name of the per account synclist, and the
# associated distribution name, and distribution base_path
GALAXY_API_SYNCLIST_NAME_FORMAT = "{account_name}-synclist"

# Require approval for incoming content, which uses a staging repository
GALAXY_REQUIRE_CONTENT_APPROVAL = True

# Local rest framework settings
# -----------------------------

GALAXY_EXCEPTION_HANDLER = "galaxy_ng.app.api.exceptions.exception_handler"
GALAXY_PAGINATION_CLASS = "pulp_ansible.app.galaxy.v3.pagination.LimitOffsetPagination"

# Galaxy authentication classes are used to set REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES
GALAXY_AUTHENTICATION_CLASSES = [
    "galaxy_ng.app.auth.session.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication",
    "rest_framework.authentication.BasicAuthentication",
    "ansible_base.jwt_consumer.hub.auth.HubJWTAuth",
]

REST_FRAMEWORK__DEFAULT_PERMISSION_CLASSES = (
    "galaxy_ng.app.access_control.access_policy.AccessPolicyBase",
)

REST_FRAMEWORK__DEFAULT_RENDERER_CLASSES = [
    'rest_framework.renderers.JSONRenderer',
    'galaxy_ng.app.renderers.CustomBrowsableAPIRenderer'
]

# Settings for insights mode
# GALAXY_AUTHENTICATION_CLASSES = ["galaxy_ng.app.auth.auth.RHIdentityAuthentication"]

# set to 'insights' for cloud.redhat.com deployments
GALAXY_DEPLOYMENT_MODE = 'standalone'

# Dictionary with True|False values for the application to turn on/off features
GALAXY_FEATURE_FLAGS = {
    'display_repositories': True,
    'execution_environments': True,  # False will make execution_environments endpoints 404
    'legacy_roles': False,
    'ai_deny_index': False,  # False will make _ui/v1/ai_deny_index/ to 404
    'dab_resource_registry': True,  # Always True, but kept because the flag may be check elsewhere
    'external_authentication': False,
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 9,  # Overridable by GALAXY_MINIMUM_PASSWORD_LENGTH
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Compatibility settings
# ----------------------
X_PULP_CONTENT_HOST = "localhost"
X_PULP_CONTENT_PORT = 24816

# Example setting of CONTENT_BIND if unix sockets are used
# CONTENT_BIND = "unix:/var/run/pulpcore-content/pulpcore-content.sock"

CONTENT_BIND = None

# This is example of how to set this via enviroment variables via dynaconf
# SPECTACULAR_SETTINGS__TITLE = "Automation Hub API __TITLE"

SPECTACULAR_SETTINGS = {
    "TITLE": "Automation Hub API",
    "DESCRIPTION": "Fetch, Upload, Organize, and Distribute Ansible Collections",
    "VERSION": "v3",
    "LICENSE": {
        "name": "GPLv2+",
        "url": "https://raw.githubusercontent.com/ansible/galaxy_ng/master/LICENSE",
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "dynaconf_merge": True,
    "DEFAULT_GENERATOR_CLASS": "galaxy_ng.openapi.GalaxySchemaGenerator",
}

# Disable django guardian anonymous user
# https://django-guardian.readthedocs.io/en/stable/configuration.html#anonymous-user-name
ANONYMOUS_USER_NAME = None

# L10N settings
USE_L10N = True
USE_I18N = True

# Default language
LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    # Django 3.0+ requires the language defined in LANGUAGE_CODE to be in this list
    ('en-us', 'English (USA)'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('nl', 'Dutch'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('zh-hans', 'Chinese'),
]

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOCALE_PATHS = (os.path.join(BASE_DIR, 'locale'),)

CONNECTED_ANSIBLE_CONTROLLERS = []

GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS = False
GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD = False

GALAXY_ENABLE_API_ACCESS_LOG = False
# Extra AUTOMATED_LOGGING settings are defined on dynaconf_hooks.py
# to be overridden by the /etc/pulp/settings.py
# or environment variable PULP_GALAXY_ENABLE_API_ACCESS_LOG

SOCIAL_AUTH_KEYCLOAK_KEY = None
SOCIAL_AUTH_KEYCLOAK_SECRET = None
SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = None

# Extra KEYCLOAK Logout URL
SOCIAL_AUTH_KEYCLOAK_LOGOUT_URL = None
KEYCLOAK_PROTOCOL = None
KEYCLOAK_HOST = None
KEYCLOAK_PORT = None
KEYCLOAK_REALM = None
# Extra KEYCLOAK settings are defined on dynaconf_hooks.py
# to be overridden by the /etc/pulp/settings.py
# or environment variable PULP_SOCIAL_AUTH_KEYCLOAK_KEY etc...

# This is used to enable or disable SSL validation on calls to the
# keycloak server. This setting has 3 options:
# False: SSL certificates are never verified.
# True: Valid SSL certificates are required. If this is set, the curl CA
#   bundle is used to validate server certs.
# /path/to/certfile: A custom CA certificate can be provided. If this is
#   set automation hub will use the CA certs in the file to validate
#   the keycloak's SSL certificate.
GALAXY_VERIFY_KEYCLOAK_SSL_CERTS = False

# Default values for signing feature
# Turn this on to enable the upload of signature
# UI looks for this setting to add the upload controls.
# this does't affect the API, upload is handled by pulp api directly
GALAXY_SIGNATURE_UPLOAD_ENABLED = False

# Turn this on to require at least one signature to be present
# on the /move/ endpoint to be able to move/approve
# to GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH (published)
# This can only be set to True if GALAXY_REQUIRE_CONTENT_APPROVAL is also True
GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL = False

# With this set to True, all the approved collections will be also signed
GALAXY_AUTO_SIGN_COLLECTIONS = False

# This sets the name of the signing service to be used for signing collections
GALAXY_COLLECTION_SIGNING_SERVICE = None

# This sets the name of the signing service to be used for signing containers
GALAXY_CONTAINER_SIGNING_SERVICE = None

AUTH_LDAP_SERVER_URI = None
AUTH_LDAP_BIND_DN = None
AUTH_LDAP_BIND_PASSWORD = None
AUTH_LDAP_USER_SEARCH_BASE_DN = None
AUTH_LDAP_USER_SEARCH_SCOPE = None
AUTH_LDAP_USER_SEARCH_FILTER = None
AUTH_LDAP_GROUP_SEARCH_BASE_DN = None
AUTH_LDAP_GROUP_SEARCH_SCOPE = None
AUTH_LDAP_GROUP_SEARCH_FILTER = None
# Extra LDAP settings are defined on dynaconf_hooks.py
# to be overriden by the /etc/pulp/settings.py
# or environment variable PULP_AUTH_LDAP_SERVER_URI etc ...


# This allows users to set AUTH backend using `ldap` or `keycloak` without the need
# to change the backends directly in the settings
# options are `ldap` and `keycloak` for defined presets
# `local` to use the unchanged defaults
# `custom` to allow the override of AUTHENTICATION_BACKENDS variable.
AUTHENTICATION_BACKEND_PRESET = 'local'  # 'ldap' or 'keycloak' or 'local' or 'custom'
AUTHENTICATION_BACKEND_PRESETS_DATA = {
    'ldap': [
        "galaxy_ng.app.auth.ldap.GalaxyLDAPBackend",
        "django.contrib.auth.backends.ModelBackend",
        "pulpcore.backends.ObjectRolePermissionBackend"
    ],
    'keycloak': [
        "social_core.backends.keycloak.KeycloakOAuth2",
        "dynaconf_merge",
    ]
}


# Enable the api/$PREFIX/v1 api for legacy roles.
GALAXY_ENABLE_LEGACY_ROLES = False

SOCIAL_AUTH_GITHUB_BASE_URL = os.environ.get('SOCIAL_AUTH_GITHUB_BASE_URL', 'https://github.com')
SOCIAL_AUTH_GITHUB_API_URL = os.environ.get('SOCIAL_AUTH_GITHUB_API_URL', 'https://api.github.com')
SOCIAL_AUTH_GITHUB_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_KEY')
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_SECRET')


# When set to True, galaxy will only load ldap groups into local
# groups that already exist in the database. Ex: if user with ldap
# groups foo and bar login and only group foo exists in the system,
# the user will be added to foo and bar will be ignored.
GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS = False

# Enables Metrics collection for Lightspeed/Wisdom
# - django command metrics-collection-lightspeed
GALAXY_METRICS_COLLECTION_LIGHTSPEED_ENABLED = True
# Enables Metrics collection for Automation Analytics
# - django command metrics-collection-automation-analytics
GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_ENABLED = False
# List of values has the insights_analytics_collector/package.py:SHIPPING_AUTH_*
GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE = "user-pass"
# URL of Ingress upload API in console.redhat.com
GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL = None
# RH account's user
GALAXY_METRICS_COLLECTION_REDHAT_USERNAME = None
# RH account's password
GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD = None
# RH account's org id (required for x-rh-identity auth type)
GALAXY_METRICS_COLLECTION_ORG_ID = None

# When set to True will enable the DYNAMIC settings feature
# Individual allowed dynamic keys are set on ./dynamic_settings.py
GALAXY_DYNAMIC_SETTINGS = False

# DJANGO ANSIBLE BASE RESOURCES REGISTRY SETTINGS
ANSIBLE_BASE_RESOURCE_CONFIG_MODULE = "galaxy_ng.app.api.resource_api"
ANSIBLE_BASE_ORGANIZATION_MODEL = "galaxy.Organization"
ANSIBLE_BASE_TEAM_MODEL = "galaxy.Team"
ANSIBLE_BASE_JWT_VALIDATE_CERT = False

# This is meant to be a url to the resource server
# which the JWT consumer code can obtain a certificate
# from for decrypting the JWT. If the hub system can
# reach the resource server via an internal url,
# use that here for the best network performance.
ANSIBLE_BASE_JWT_KEY = None

# NOTE: For the Resource Sync Feature the following are required:
# RESOURCE_SERVER = {"URL": str, "SECRET_KEY": str, "VALIDATE_HTTPS": bool}

# -- ANSIBLE BASE RBAC --
# If a role does not already exist that can give those object permissions
# then the system must create one, this is used for naming the auto-created role
ANSIBLE_BASE_ROLE_CREATOR_NAME = "{obj._meta.model_name} Creator Role"
# Require change permission to get delete permission
ANSIBLE_BASE_DELETE_REQUIRE_CHANGE = False
# For assignments
ANSIBLE_BASE_ALLOW_TEAM_PARENTS = False
ANSIBLE_BASE_ALLOW_TEAM_ORG_ADMIN = False
ANSIBLE_BASE_ALLOW_TEAM_ORG_MEMBER = True
# For role definitions
ANSIBLE_BASE_ALLOW_CUSTOM_TEAM_ROLES = True
# required for user level rbac roles&permissions
ANSIBLE_BASE_ALLOW_SINGLETON_USER_ROLES = True
ANSIBLE_BASE_ALLOW_SINGLETON_TEAM_ROLES = True
# Pass ignore_conflicts=False for bulk_create calls for role evaluations
ANSIBLE_BASE_EVALUATIONS_IGNORE_CONFLICTS = False
# Set up managed role definitions
ANSIBLE_BASE_MANAGED_ROLE_REGISTRY = {
    'platform_auditor': {'name': 'Platform Auditor', 'shortname': 'sys_auditor'},
    'sys_auditor': {'shortname': 'sys_auditor'},
    # member role is duplicated, either should work, but we have 2 for latter ownership issues
    'galaxy_only_team_member': {'name': 'Galaxy Team Member', 'shortname': 'team_member'},
    'team_member': {},
    'team_admin': {},
    # TODO: add organization to the registry later
    # 'org_admin': {},
    # 'org_member': {},
}

# WARNING: This setting is used in database migrations to create a default organization.
DEFAULT_ORGANIZATION_NAME = "Default"

# If False it disables editing and managing users and groups.
ALLOW_LOCAL_RESOURCE_MANAGEMENT = True
