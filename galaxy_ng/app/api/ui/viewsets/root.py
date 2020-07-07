from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.constants import UIAPIVersions


class APIRootView(api_base.ViewSet):
    def list(self, request, *args, **kwargs):
        return Response({
            'current_version': UIAPIVersions.CURRENT.value,
            'available_versions': UIAPIVersions.ALL.value
        })
