from django.conf import settings
from django.urls import include, path

from galaxy_ng.app.api import urls as api_urls
from galaxy_ng.ui import urls as ui_urls

API_PATH_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip('/')

app_name = "galaxy"
urlpatterns = [
    path("", include(ui_urls)),
    path(f"{API_PATH_PREFIX}/", include(api_urls)),
    path('', include('django_prometheus.urls')),
]
