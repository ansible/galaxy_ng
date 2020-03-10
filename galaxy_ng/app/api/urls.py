from django.urls import include, path

from . import views
from .ui import urls as ui_urls
from .v3 import urls as v3_urls


app_name = "api"
urlpatterns = [
    path("", views.ApiRootView.as_view(), name="root"),
    path("v3/", include(v3_urls)),
    path("v3/_ui/", include(ui_urls)),

    # This path is to redirect requests to /api/automation-hub/api/
    # to /api/automation-hub/

    # This is a workaround for https://github.com/ansible/ansible/issues/62073.
    # ansible-galaxy in ansible 2.9 always appends '/api' to any configured
    # galaxy server urls to try to find the API root. So add a redirect from
    # "/api" to actual API root at "/".

    # This can be removed when ansible-galaxy stops appending '/api' to the
    # urls.
    path("api/", views.SlashApiRedirectView.as_view()),
]
