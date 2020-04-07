from django.conf import settings
from django.urls import include, path

from galaxy_ng.app.api import urls as api_urls

API_PATH_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip('/')

app_name = "galaxy"
urlpatterns = [
    path(f"{API_PATH_PREFIX}/", include(api_urls)),
    path('', include('django_prometheus.urls')),
]
