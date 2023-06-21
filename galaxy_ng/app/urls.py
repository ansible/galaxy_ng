from django.conf import settings
from django.conf.urls import url
from django.shortcuts import redirect
from django.urls import include, path

from . import views
from galaxy_ng.app.api import urls as api_urls
from galaxy_ng.ui import urls as ui_urls

API_PATH_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")

galaxy_urls = [
    path(f"{API_PATH_PREFIX}/", include(api_urls)),
]

urlpatterns = [
    path("", include((galaxy_urls, "api"), namespace="galaxy")),
    path("", include(ui_urls)),
    path("", include("django_prometheus.urls")),
    path(
        f"{API_PATH_PREFIX}/v3/openapi.json",
        views.PulpOpenAPIJsonRedirectView.as_view(),
        name="schema-json-redirect",
    ),
    path(
        f"{API_PATH_PREFIX}/v3/openapi.yaml",
        views.PulpOpenAPIYamlRedirectView.as_view(),
        name="schema-yaml-redirect",
    ),
    path(
        f"{API_PATH_PREFIX}/v3/redoc/",
        views.PulpRedocRedirectView.as_view(),
        name="schema-redoc-redirect",
    ),
    path(
        f"{API_PATH_PREFIX}/v3/swagger-ui/",
        views.PulpSwaggerRedirectView.as_view(),
        name="swagger-ui-redirect",
    ),
    path("healthz", views.health_view),
]

if settings.get("API_ROOT") != "/pulp/":
    urlpatterns.append(
        path(
            "pulp/api/<path:api_path>",
            views.PulpAPIRedirectView.as_view(),
            name="pulp_redirect")
    )

if settings.get("SOCIAL_AUTH_KEYCLOAK_KEY"):
    urlpatterns.append(url("", include("social_django.urls", namespace="social")))
    urlpatterns.append(path("login/",
                       lambda request: redirect("/login/keycloak/", permanent=False)))

if settings.get("SOCIAL_AUTH_GITHUB_KEY"):
    urlpatterns.append(url('', include('social_django.urls', namespace='github')))
