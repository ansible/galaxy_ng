from django.http import HttpResponseRedirect

from rest_framework.response import Response
from rest_framework.reverse import reverse

from galaxy_ng.app.api import base as api_base


class ApiRootView(api_base.APIView):
    def get(self, request):
        data = {
            "available_versions": {"v3": "v3/"},
        }
        return Response(data)


class SlashApiRedirectView(api_base.APIView):
    """Redirect requests to /api/automation-hub/api/ to /api/automation-hub/

    This is a workaround for https://github.com/ansible/ansible/issues/62073.
    This can be removed when ansible-galaxy stops appending '/api' to the url."""
    def get(self, request):
        return HttpResponseRedirect(reverse('galaxy:api:root'), status=307)
