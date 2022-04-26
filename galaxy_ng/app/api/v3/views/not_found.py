from galaxy_ng.app.api import base as api_base
from django.http import HttpResponseNotFound


class NotFoundView(api_base.APIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return HttpResponseNotFound()
