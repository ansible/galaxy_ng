import os


PROMETHEUS_BEFORE_MIDDLEWARE = 'django_prometheus.middleware.PrometheusBeforeMiddleware'
PROMETHEUS_AFTER_MIDDLEWARE = 'django_prometheus.middleware.PrometheusAfterMiddleware'
PROM_ACCT_BEFORE = 'galaxy_ng.contrib.metrics_middleware.AccountEnhancedMetricsBeforeMiddleware'
PROM_ACCT_AFTER = 'galaxy_ng.contrib.metrics_middleware.AccountEnhancedMetricsAfterMiddleware'
ACCOUNT_ENHANCED_METRICS = os.environ.get('ACCOUNT_ENHANCED_METRICS', False) in (True, 'True')
if ACCOUNT_ENHANCED_METRICS:
    PROMETHEUS_BEFORE_MIDDLEWARE = PROM_ACCT_BEFORE
    PROMETHEUS_AFTER_MIDDLEWARE = PROM_ACCT_AFTER

MIDDLEWARE = [
    PROMETHEUS_BEFORE_MIDDLEWARE,
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
    PROMETHEUS_AFTER_MIDDLEWARE,
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

ALLOWED_CONTENT_CHECKSUMS = ["sha224", "sha256", "sha384", "sha512"]

# Compatibility settings
# ----------------------
# FIXME(cutwater): To be removed after viewsets stop proxying API requests
#                  to pulp_ansible.

X_PULP_API_HOST = "localhost"
X_PULP_API_PORT = 8000
X_PULP_API_USER = "admin"
X_PULP_API_PASSWORD = "admin"
X_PULP_API_PREFIX = "pulp_ansible/galaxy/automation-hub/api"

X_PULP_CONTENT_HOST = "localhost"
X_PULP_CONTENT_PORT = 24816
