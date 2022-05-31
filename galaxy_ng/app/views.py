from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.conf import settings
from galaxy_ng.app.api import base as api_base


def health_view(request):
    return HttpResponse('OK')


class HttpResponsePermanentRedirect308(HttpResponsePermanentRedirect):
    status_code = 308


class PulpAPIRedirectView(api_base.APIView):
    permission_classes = []

    def get(self, request, api_path):
        url = f"/{settings.API_ROOT.strip('/')}/api/{api_path.strip('/')}/"

        args = request.META.get("QUERY_STRING", "")
        if args:
            url = "%s?%s" % (url, args)

        # Returning 308 instead of 302 since 308 requires that clients maintain the
        # same method as the original request.
        return HttpResponsePermanentRedirect308(url)
