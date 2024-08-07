from django.urls import re_path as url
from django.views.generic import RedirectView


urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/ui/")),
    url('hub', RedirectView.as_view(url="/hub/")),
    #url('hub/', RedirectView.as_view(url="/hub/index.html")),
    #url(r'^hub', RedirectView.as_view(url="/static/galaxy_ng/index.html")),
]
