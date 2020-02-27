from django.conf import settings
from django.urls import include, path

from pulp_galaxy.app.api import urls as api_urls

app_name = "galaxy"
urlpatterns = [
    path(settings.X_GALAXY_API_ROOT, include(api_urls)),
]
