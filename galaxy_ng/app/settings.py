
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
    "DEFAULT_GENERATOR_CLASS": "galaxy_ng.openapi.schema_generator.GalaxySchemaGenerator",
    "VERSION": "v3",
    "LICENSE": {
        "name": "GPLv2+",
        "url": "https://raw.githubusercontent.com/ansible/galaxy_ng/master/LICENSE",
    },
    # Create separate components for PATCH endpoints (without required list) default:True
    'COMPONENT_SPLIT_PATCH': False,
    # Split components into request and response parts where appropriate default: False
    'COMPONENT_SPLIT_REQUEST': False,
    # Aid client generator targets that have trouble with read-only properties. default: False
    'COMPONENT_NO_READ_ONLY_REQUIRED': False,

    "SWAGGER_UI_SETTINGS": {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": False,
        "docExpansion": "list",
    },
    "ENUM_NAME_OVERRIDES": {
        "SynclistPolicyEnum": 'galaxy_ng.app.models.synclist.SyncList.POLICY_CHOICES',
        "RemotePolicyEnum": 'pulpcore.plugin.models.Remote.POLICY_CHOICES',
        "ContainerManifestMediaTypeEnum": 'pulp_container.app.models.Manifest.MANIFEST_CHOICES',
        "ContainerBlobMediaTypeEnum": 'pulp_container.app.models.Blob.BLOB_CHOICES',
    },
    "TAGS": [
        {"name": "Galaxy: Collection"},
        {"name": "Galaxy: Collection Version"},
        {"name": "Galaxy: Collection Version Artifact"},
        {"name": "Galaxy: Collection Version Artifact Import"},
        {"name": "Galaxy: Collection Namespace",
         "description": "Namespaces used by ansible collections"},
        {"name": "Galaxy: Sync"},
        {"name": "Galaxy: Task"},
        {"name": "Galaxy: Auth"},
        {"name": "Galaxy: API"},
        {"name": "Galaxy UI: Collection"},
        {"name": "Galaxy UI: Collection Version"},
        {"name": "Galaxy UI: Collection Version Artifact Import"},
        {"name": "Galaxy UI: Collection Remote"},
        {"name": "Galaxy UI: Distribution"},
        {"name": "Galaxy UI: Synclist"},
        {"name": "Galaxy UI: Container Namespace"},
        {"name": "Galaxy UI: Container Repository"},
        {"name": "Galaxy UI: Container Repository Manifest"},
        {"name": "Galaxy UI: Container Repository History"},
        {"name": "Galaxy UI: Container Readme"},
        {"name": "Galaxy UI: Group"},
        {"name": "Galaxy UI: User"},
        {"name": "Galaxy UI: Namespace"},
        {"name": "Galaxy UI: Tag"},
        {"name": "Galaxy UI: Feature Flags"},
        {"name": "Galaxy UI: Auth"},
        {"name": "Galaxy UI: API"},
    ],
    "dynaconf_merge": True,
}

# Disable django guardian anonymous user
# https://django-guardian.readthedocs.io/en/stable/configuration.html#anonymous-user-name
ANONYMOUS_USER_NAME = None
