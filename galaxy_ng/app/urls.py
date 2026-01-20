from django.conf import settings
from django.urls import re_path as url
from django.shortcuts import redirect
from django.urls import include, path

from . import views
from galaxy_ng.app.api import urls as api_urls
from galaxy_ng.ui import urls as ui_urls

from ansible_base.resource_registry.urls import (
    urlpatterns as resource_api_urls,
)
from ansible_base.rbac.service_api.urls import rbac_service_urls
from ansible_base.feature_flags.urls import api_version_urls as feature_flags_urls

API_PATH_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")

galaxy_urls = [
    path(f"{API_PATH_PREFIX}/", include(api_urls)),
]

urlpatterns = [
    path("", include((galaxy_urls, "api"), namespace="galaxy")),
    path("", include(ui_urls)),
    path("", include("django_prometheus.urls")),
    # Static OpenAPI spec for Galaxy NG (user-facing endpoints only)
    path(
        f"{API_PATH_PREFIX}/v3/galaxy.json",
        views.StaticOpenAPIView.as_view(),
        name="schema",
    ),
    # Backward compatible alias for /v3/openapi.json
    # Keeping this endpoint to avoid breaking existing clients that may be using the old URL.
    # Tests (test_auth_openapi.py) and Swagger UI reference the "schema" name for reverse lookups.
    path(
        f"{API_PATH_PREFIX}/v3/openapi.json",
        views.StaticOpenAPIView.as_view(),
        name="openapi-schema",
    ),
    # Full Pulp OpenAPI spec (all endpoints including Pulp-internal)
    path(
        f"{API_PATH_PREFIX}/v3/galaxy-pulp.json",
        views.ProtectedSpectacularJSONAPIView.as_view(),
        name="pulp-schema",
    ),
    path(
        f"{API_PATH_PREFIX}/v3/openapi.yaml",
        views.ProtectedSpectacularYAMLAPIView.as_view(),
        name="schema-yaml",
    ),
    path(
        f"{API_PATH_PREFIX}/v3/redoc/",
        views.ProtectedSpectacularRedocView.as_view(),
        name="schema-redoc",
    ),
    path(
        f"{API_PATH_PREFIX}/v3/swagger-ui/",
        views.ProtectedSpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("healthz", views.health_view),
]

urlpatterns.append(path(f"{API_PATH_PREFIX}/", include(resource_api_urls)))
urlpatterns.append(path(f"{API_PATH_PREFIX}/", include(rbac_service_urls)))
urlpatterns.append(path(f"{API_PATH_PREFIX}/", include(feature_flags_urls)))
# urlpatterns.append(path(f"{API_PATH_PREFIX}/", include(dab_rbac_urls)))

if settings.get("API_ROOT") != "/pulp/":
    urlpatterns.append(
        path("pulp/api/<path:api_path>", views.PulpAPIRedirectView.as_view(), name="pulp_redirect")
    )

if settings.get("SOCIAL_AUTH_KEYCLOAK_KEY"):
    urlpatterns.append(url("", include("social_django.urls", namespace="social")))
    urlpatterns.append(
        path("login/", lambda request: redirect("/login/keycloak/", permanent=False))
    )

if settings.get("SOCIAL_AUTH_GITHUB_KEY"):
    urlpatterns.append(url("", include("social_django.urls", namespace="github")))
