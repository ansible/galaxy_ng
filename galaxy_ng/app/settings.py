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

# The default repo and distro is called 'automation-hub', as
# created by the initial-data.json data fixture
GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH = "automation-hub"

# Require approval for incoming content,
# currently using a certification flag,
# later using a staging repository
GALAXY_REQUIRE_CONTENT_APPROVAL = True

# Local rest framework settings
# -----------------------------

GALAXY_EXCEPTION_HANDLER = "galaxy_ng.app.api.exceptions.exception_handler"
GALAXY_PAGINATION_CLASS = "galaxy_ng.app.api.pagination.LimitOffsetPagination"
GALAXY_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication",
]
GALAXY_PERMISSION_CLASSES = [
    'rest_framework.permissions.IsAuthenticated',
]
# Settings for insights mode
# GALAXY_AUTHENTICATION_CLASSES = ["galaxy_ng.app.auth.auth.RHIdentityAuthentication"]
# GALAXY_PERMISSION_CLASSES = ['galaxy_ng.app.auth.auth.RHEntitlementRequired']

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
