from django.http import HttpResponseRedirect

from rest_framework.response import Response
from rest_framework.reverse import reverse

from galaxy_ng.app.api import base as api_base


class ApiRootView(api_base.APIView):
    def get(self, request, *args, **kwargs):
        data = {
            "available_versions": {"v3": "v3/"},
        }

        if kwargs.get("path"):
            data["distro_base_path"] = kwargs["path"]

        return Response(data)


class ApiRedirectView(api_base.APIView):
    """Redirect requests to /api/automation-hub/api/ to /api/automation-hub/

    This is a workaround for https://github.com/ansible/ansible/issues/62073.
    This can be removed when ansible-galaxy stops appending '/api' to the url."""

    def get(self, request, *args, **kwargs):
        reverse_url_name = kwargs.get("reverse_url_name")

        reverse_kwargs = {}
        if "path" in kwargs:
            reverse_kwargs["path"] = kwargs["path"]

        return HttpResponseRedirect(reverse(reverse_url_name,
                                            kwargs=reverse_kwargs), status=307)
