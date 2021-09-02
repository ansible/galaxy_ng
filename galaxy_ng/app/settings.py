import os
from pathlib import Path

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
GALAXY_PAGINATION_CLASS = "galaxy_ng.app.api.pagination.LimitOffsetPagination"
GALAXY_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication",
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

GALAXY_ENABLE_API_ACCESS_LOG = os.getenv('GALAXY_ENABLE_API_ACCESS_LOG', default=False)

if GALAXY_ENABLE_API_ACCESS_LOG:
    INSTALLED_APPS.append('automated_logging')
    MIDDLEWARE.append('automated_logging.middleware.AutomatedLoggingMiddleware')
    LOGGING = {
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
    AUTOMATED_LOGGING = {
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
                "mask": ["password"],
                "query": False,
            },
            "exclude": {
                "applications": [],
                "methods": ["GET"],
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

# Obtain values for Social Auth
SOCIAL_AUTH_KEYCLOAK_KEY = os.getenv('SOCIAL_AUTH_KEYCLOAK_KEY', default=None)
SOCIAL_AUTH_KEYCLOAK_SECRET = os.getenv('SOCIAL_AUTH_KEYCLOAK_SECRET', default=None)
SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY = os.getenv('SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY', default=None)
KEYCLOAK_PROTOCOL = os.getenv('KEYCLOAK_PROTOCOL', default=None)
KEYCLOAK_HOST = os.getenv('KEYCLOAK_HOST', default=None)
KEYCLOAK_PORT = os.getenv('KEYCLOAK_PORT', default=None)
KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', default=None)

# Add settings if Social Auth values are provided
if (SOCIAL_AUTH_KEYCLOAK_KEY and SOCIAL_AUTH_KEYCLOAK_SECRET
        and SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY and KEYCLOAK_HOST
        and KEYCLOAK_PORT and KEYCLOAK_REALM):
    KEYCLOAK_ADMIN_ROLE = os.getenv('KEYCLOAK_ADMIN_ROLE', default='hubadmin')
    KEYCLOAK_GROUP_TOKEN_CLAIM = os.getenv('KEYCLOAK_GROUP_TOKEN_CLAIM', default='group')
    KEYCLOAK_ROLE_TOKEN_CLAIM = os.getenv('KEYCLOAK_GROUP_TOKEN_CLAIM', default='client_roles')
    KEYCLOAK_HOST_LOOPBACK = os.getenv('KEYCLOAK_HOST_LOOPBACK', default=None)
    KEYCLOAK_URL = "{protocol}://{host}:{port}".format(protocol=KEYCLOAK_PROTOCOL,
                                                       host=KEYCLOAK_HOST, port=KEYCLOAK_PORT)
    auth_url_str = "{keycloak}/auth/realms/{realm}/protocol/openid-connect/auth/"
    SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = auth_url_str.format(keycloak=KEYCLOAK_URL,
                                                                 realm=KEYCLOAK_REALM)
    if KEYCLOAK_HOST_LOOPBACK:
        loopback_url = "{protocol}://{host}:{port}".format(protocol=KEYCLOAK_PROTOCOL,
                                                           host=KEYCLOAK_HOST_LOOPBACK,
                                                           port=KEYCLOAK_PORT)
        SOCIAL_AUTH_KEYCLOAK_AUTHORIZATION_URL = auth_url_str.format(keycloak=loopback_url,
                                                                     realm=KEYCLOAK_REALM)
    token_url_str = "{keycloak}/auth/realms/{realm}/protocol/openid-connect/token/"
    SOCIAL_AUTH_KEYCLOAK_ACCESS_TOKEN_URL = token_url_str.format(keycloak=KEYCLOAK_URL,
                                                                 realm=KEYCLOAK_REALM)

    SOCIAL_AUTH_LOGIN_REDIRECT_URL = os.getenv('SOCIAL_AUTH_LOGIN_REDIRECT_URL', default='/ui/')
    SOCIAL_AUTH_POSTGRES_JSONFIELD = True
    SOCIAL_AUTH_JSONFIELD_CUSTOM = 'django.contrib.postgres.fields.JSONField'
    SOCIAL_AUTH_URL_NAMESPACE = 'social'
    SOCIAL_AUTH_KEYCLOAK_EXTRA_DATA = [('refresh_token', 'refresh_token'),
                                       (KEYCLOAK_ROLE_TOKEN_CLAIM, KEYCLOAK_ROLE_TOKEN_CLAIM), ]

    SOCIAL_AUTH_PIPELINE = (
        'social_core.pipeline.social_auth.social_details',
        'social_core.pipeline.social_auth.social_uid',
        'social_core.pipeline.social_auth.social_user',
        'social_core.pipeline.user.get_username',
        'social_core.pipeline.social_auth.associate_by_email',
        'social_core.pipeline.user.create_user',
        'social_core.pipeline.social_auth.associate_user',
        'social_core.pipeline.social_auth.load_extra_data',
        'social_core.pipeline.user.user_details',
        'galaxy_ng.app.pipelines.user_role',
        'galaxy_ng.app.pipelines.user_group',
    )

    # Set external authentication feature flag
    GALAXY_FEATURE_FLAGS["external_authentication"] = True

    # Add to installed apps
    INSTALLED_APPS.append('social_django')

    # Add to authentication backends
    AUTHENTICATION_BACKENDS = [
        'social_core.backends.keycloak.KeycloakOAuth2',
        'dynaconf_merge',
    ]

    GALAXY_AUTHENTICATION_CLASSES = [
        "rest_framework.authentication.SessionAuthentication",
        "galaxy_ng.app.auth.token.ExpiringTokenAuthentication",
    ]

    # Set default to one day expiration
    GALAXY_TOKEN_EXPIRATION = 1440

    # Build paths inside the project like this: BASE_DIR / ...
    BASE_DIR = Path(__file__).absolute().parent

    # Add to templates
    TEMPLATES = [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [BASE_DIR / "templates"],
            "APP_DIRS": True,
            "OPTIONS": {
                "context_processors": [
                    # BEGIN: Pulp standard context processors
                    "django.template.context_processors.debug",
                    "django.template.context_processors.request",
                    "django.contrib.auth.context_processors.auth",
                    "django.contrib.messages.context_processors.messages",
                    # END: Pulp standard context processors
                    'social_django.context_processors.backends',
                    'social_django.context_processors.login_redirect',
                ],
            },
        },
    ]
