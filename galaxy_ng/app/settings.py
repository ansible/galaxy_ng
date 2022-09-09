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
    # END: Pulp standard middleware
    'django_prometheus.middleware.PrometheusAfterMiddleware',
    'django_currentuser.middleware.ThreadLocalUserMiddleware',
]

INSTALLED_APPS = [
    'rest_framework.authtoken',
    'dynaconf_merge',
]


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
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication",
    "rest_framework.authentication.BasicAuthentication",
]

REST_FRAMEWORK__DEFAULT_PERMISSION_CLASSES = (
    "galaxy_ng.app.access_control.access_policy.AccessPolicyBase",
)

# Settings for insights mode
# GALAXY_AUTHENTICATION_CLASSES = ["galaxy_ng.app.auth.auth.RHIdentityAuthentication"]

# set to 'insights' for cloud.redhat.com deployments
GALAXY_DEPLOYMENT_MODE = 'standalone'

# Dictionary with True|False values for the application to turn on/off features
GALAXY_FEATURE_FLAGS = {
    'execution_environments': True,  # False will make execution_environments endpoints 404
    'legacy_roles': False,
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
        "django_auth_ldap.backend.LDAPBackend",
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
SOCIAL_AUTH_GITHUB_API_URL = os.environ.get('SOCIAL_AUTH_GITHUB_BASE_URL', 'https://api.github.com')
SOCIAL_AUTH_GITHUB_KEY = os.environ.get('SOCIAL_AUTH_GITHUB_KEY')
SOCIAL_AUTH_GITHUB_SECRET = os.environ.get('SOCIAL_AUTH_GITHUB_SECRET')
