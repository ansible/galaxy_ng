from django.conf import settings
from django.urls import include, path

from pulp_galaxy.app.api import urls as api_urls

app_name = "galaxy"
urlpatterns = [
    path(f"{settings.API_PATH_PREFIX}/", include(api_urls)),
]
