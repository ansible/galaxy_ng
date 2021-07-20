from django.apps import apps
from django.http import HttpResponseRedirect

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse

from galaxy_ng.app.api import base as api_base


class ApiRootView(api_base.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        data = {
            "available_versions": {"v3": "v3/"},
            "server_version": apps.get_app_config("galaxy").version,
            "galaxy_ng_version": apps.get_app_config("galaxy").version,
            "pulp_ansible_version": apps.get_app_config('ansible').version,
        }

        if kwargs.get("path"):
            data["distro_base_path"] = kwargs["path"]

        return Response(data)


class ApiRedirectView(api_base.APIView):
    permission_classes = [IsAuthenticated]

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
