# FIXME(cutwater): 1. Rename GALAXY_API_ROOT in pulp-ansible to ANSIBLE_API_ROOT
#                  2. Rename API_PATH_PREFIX to GALAXY_API_ROOT
API_PATH_PREFIX = "api/galaxy"


X_PULP_API_HOST = "localhost"
X_PULP_API_PORT = 8000
X_PULP_API_USER = "admin"
X_PULP_API_PASSWORD = "admin"
X_PULP_API_PREFIX = "pulp_ansible/galaxy/automation-hub/api"


REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "pulp_galaxy.app.api.pagination.LimitOffsetPagination",
    "dynaconf_merge": True,
}

PULP_CONTENT_HOST = "pulp-content"
PULP_CONTENT_PORT = 24816
PULP_CONTENT_PATH_PREFIX = f"/{API_PATH_PREFIX}/v3/artifacts/collections/"
