from django.conf import settings
from django.urls import include, path

from . import views
from galaxy_ng.app.api import urls as api_urls
from galaxy_ng.app import customadmin as admin
from galaxy_ng.ui import urls as ui_urls
from galaxy_ng.app.api.views import (
    JSONAPIView,
    YAMLAPIView,
    RedocView,
    SwaggerView,
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
    path("healthz", views.health_view),
]

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/openapi.json",
        JSONAPIView.as_view(),
        name="schema",
    )
)

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/openapi.yaml",
        YAMLAPIView.as_view(),
        name="schema-yaml",
    )
)

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/redoc/",
        RedocView.as_view(),
        name="schema-redoc",
    )
)

urlpatterns.append(
    path(
        f"{API_PATH_PREFIX}/v3/swagger-ui/",
        SwaggerView.as_view(url_name='schema', pulp_tag_name="Galaxy API"),
        name='schema-swagger-ui',
    )
)
