from django.urls import re_path as url
from django.views.generic import RedirectView


urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/ui/")),
]
