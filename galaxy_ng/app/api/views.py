import os

import galaxy_importer

from django.apps import apps
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from pulp_ansible.app.models import AnsibleDistribution

from rest_framework.response import Response
from rest_framework.reverse import reverse

from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base


# define the version matrix at the module level to avoid the redefinition on every API call.
VERSIONS = {
    "available_versions": {
        "v3": "v3/",
        "pulp-v3": "pulp/api/v3/"
    },
    "server_version": apps.get_app_config("galaxy").version,
    "galaxy_ng_version": apps.get_app_config("galaxy").version,
    "galaxy_ng_commit": os.environ.get("GIT_COMMIT", ""),
    "galaxy_importer_version": galaxy_importer.__version__,
    "pulp_core_version": apps.get_app_config('core').version,
    "pulp_ansible_version": apps.get_app_config('ansible').version,
    "pulp_container_version": apps.get_app_config('container').version,
}


# Add in v1 support if configured
if settings.GALAXY_ENABLE_LEGACY_ROLES:
    VERSIONS["available_versions"]["v1"] = "v1/"


class ApiRootView(api_base.APIView):
    permission_classes = [access_policy.AppRootAccessPolicy]
    action = "retrieve"

    def get(self, request, *args, **kwargs):
        """
        Returns the version matrix for the API + the current distro.
        """
        data = {**VERSIONS}

        if kwargs.get("path"):
            distro = get_object_or_404(
                AnsibleDistribution,
                base_path=self.kwargs["path"]
            )
            data["distro_base_path"] = distro.base_path

        return Response(data)


class ApiRedirectView(api_base.APIView):
    permission_classes = [access_policy.AppRootAccessPolicy]
    action = "retrieve"

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
