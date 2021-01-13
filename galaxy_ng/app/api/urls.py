from django.conf import settings
from django.urls import include, path

from . import views
from .ui import urls as ui_urls
from .v3 import urls as v3_urls

DEFAULT_DISTRIBUTION_BASE_PATH = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH.strip('/')

app_name = "api"


v3_urlpatterns = [
    path("", include(v3_urls.auth_urls)),
    path("", include(v3_urls.namespace_urls)),

    # Set an instance of the v3 urls/viewsets at the same
    # url path as the former galaxy_api.api.v3.viewsets
    # ie (/api/automation-hub/v3/collections etc
    # and pass in path param 'path' that actually means
    # the base_path of the Distribution. For the default case,
    # use the hard coded 'default' distro (ie, 'automation-hub')
    path(
        "",
        include((v3_urls, app_name), namespace='default-content'),
        {
            'no_path_specified': True,
            'path': DEFAULT_DISTRIBUTION_BASE_PATH,
        }
    ),
]

content_v3_urlpatterns = [
    # A set of galaxy v3 API urls per Distribution.base_path
    # which is essentially per Repository
    path("<str:path>/v3/",
         # include((v3_urls, app_name))),
         include(v3_urls)),
    path("<str:path>/v3/", include(v3_urls.sync_urls)),
]

content_urlpatterns = [
    path("content/",
         include((content_v3_urlpatterns, app_name), namespace="v3")),

    path("content/<str:path>/",
         views.ApiRootView.as_view(),
         name="root"),

    # This can be removed when ansible-galaxy stops appending '/api' to the
    # urls.
    path("content/<str:path>/api/",
         views.ApiRedirectView.as_view(),
         name="api-redirect",
         kwargs={"reverse_url_name": "galaxy:api:content:root"}),
]

urlpatterns = [
    path("v3/", include((v3_urlpatterns, app_name), namespace="v3")),

    path("_ui/", include((ui_urls, app_name), namespace="ui")),

    path("", include((content_urlpatterns, app_name), namespace='content')),

    path("",
         views.ApiRootView.as_view(),
         name="root",
         ),

    # This path is to redirect requests to /api/automation-hub/api/
    # to /api/automation-hub/

    # This is a workaround for https://github.com/ansible/ansible/issues/62073.
    # ansible-galaxy in ansible 2.9 always appends '/api' to any configured
    # galaxy server urls to try to find the API root. So add a redirect from
    # "/api" to actual API root at "/".

    # This can be removed when ansible-galaxy stops appending '/api' to the
    # urls.
    path("api/",
         views.ApiRedirectView.as_view(),
         name="api-redirect",
         kwargs={"reverse_url_name": "galaxy:api:root"}),
]
