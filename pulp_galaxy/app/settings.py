

# FIXME(cutwater): 1. Rename GALAXY_API_ROOT in pulp-ansible to ANSIBLE_API_ROOT
#                  2. Rename X_GALAXY_API_ROOT to GALAXY_API_ROOT
X_GALAXY_API_ROOT = "api/galaxy/"


X_PULP_API_HOST = "localhost"
X_PULP_API_PORT = 8000
X_PULP_API_USER = "admin"
X_PULP_API_PASSWORD = "admin"


REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "pulp_galaxy.app.api.pagination.LimitOffsetPagination",
    "dynaconf_merge": True,
}
