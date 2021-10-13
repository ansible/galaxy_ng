import os

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
ADMIN_SITE_URL = "automation-hub/admin/"

# A client connection to /api/automation-hub/ is the same as a client connection
# to /api/automation-hub/content/<GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH>/
# with the exception of galaxy_ng.app.api.v3.viewsets.CollectionUploadViewSet
GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH = "published"

GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH = "staging"
GALAXY_API_REJECTED_DISTRIBUTION_BASE_PATH = "rejected"

# The format for the name of the per account synclist, and the
# associated repository, distribution, and distribution base_paths
GALAXY_API_SYNCLIST_NAME_FORMAT = "{account_name}-synclist"

# Require approval for incoming content, which uses a staging repository
GALAXY_REQUIRE_CONTENT_APPROVAL = True

# Number of synclist to be processed in single task
SYNCLIST_BATCH_SIZE = 200

# Local rest framework settings
# -----------------------------

GALAXY_EXCEPTION_HANDLER = "galaxy_ng.app.api.exceptions.exception_handler"
GALAXY_PAGINATION_CLASS = "pulp_ansible.app.galaxy.v3.pagination.LimitOffsetPagination"
GALAXY_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication",
    "rest_framework.authentication.BasicAuthentication",
]
# Settings for insights mode
# GALAXY_AUTHENTICATION_CLASSES = ["galaxy_ng.app.auth.auth.RHIdentityAuthentication"]

# set to 'insights' for cloud.redhat.com deployments
GALAXY_DEPLOYMENT_MODE = 'standalone'

# Dictionary with True|False values for the application to turn on/off features
GALAXY_FEATURE_FLAGS = {
    'execution_environments': True,  # False will make execution_environments endpoints 404
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 9,
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
