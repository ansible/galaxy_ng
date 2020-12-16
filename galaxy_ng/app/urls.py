from django.conf import settings
from django.urls import include, path

from galaxy_ng.app.api import urls as api_urls
from galaxy_ng.app import customadmin as admin
from galaxy_ng.ui import urls as ui_urls

from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

API_PATH_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")

galaxy_urls = [
    path(f"{API_PATH_PREFIX}/", include(api_urls)),
]

urlpatterns = [
    path("", include((galaxy_urls, "api"), namespace="galaxy")),
    path("", include(ui_urls)),
    path("", include("django_prometheus.urls")),
    path(settings.ADMIN_SITE_URL, admin.site.urls),
]

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/openapi.json",
        SpectacularJSONAPIView.as_view(),
        name="schema",
    )
)

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/openapi.yaml",
        SpectacularYAMLAPIView.as_view(),
        name="schema-yaml",
    )
)

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/redoc/",
        SpectacularRedocView.as_view(),
        name="schema-redoc",
    )
)

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/swagger-ui/",
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    )
)
