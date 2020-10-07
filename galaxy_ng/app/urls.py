from django.conf import settings
from django.urls import include, path

from galaxy_ng.app.api import urls as api_urls
from galaxy_ng.app import customadmin as admin
from galaxy_ng.ui import urls as ui_urls


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
