from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app import constants


class APIRootView(api_base.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        return Response({
            'current_version': constants.CURRENT_UI_API_VERSION,
            'available_versions': constants.ALL_UI_API_VERSION
        })
