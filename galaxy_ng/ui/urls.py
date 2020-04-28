from django.conf.urls import url
from django.views.generic import RedirectView


urlpatterns = [
    url(r'^$', RedirectView.as_view(url="/ui/")),
]
