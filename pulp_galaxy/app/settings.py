# FIXME(cutwater): 1. Rename GALAXY_API_ROOT in pulp-ansible to ANSIBLE_API_ROOT
#                  2. Rename API_PATH_PREFIX to GALAXY_API_ROOT
API_PATH_PREFIX = "api/galaxy"

AUTH_USER_MODEL = 'galaxy.user'


# Local rest framework settings
# -----------------------------

GALAXY_EXCEPTION_HANDLER = "pulp_galaxy.app.api.exceptions.exception_handler"
GALAXY_PAGINATION_CLASS = "pulp_galaxy.app.api.pagination.LimitOffsetPagination"
GALAXY_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.BasicAuthentication",
    # "pulp_galaxy.app.auth.auth.RHIdentityAuthentication",
]
GALAXY_PERMISSION_CLASSES = [
    'rest_framework.permissions.IsAuthenticated',
#    'pulp_galaxy.app.auth.auth.RHEntitlementRequired',
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

X_PULP_CONTENT_HOST = "pulp-content"
X_PULP_CONTENT_PORT = 24816
X_PULP_CONTENT_PATH_PREFIX = f"/{API_PATH_PREFIX}/v3/artifacts/collections/"
