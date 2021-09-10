from django.conf import settings
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base


class SettingsView(api_base.APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        data = {}
        data['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'] = settings.get(
            'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'
        ) or False
        data['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'] = settings.get(
            'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'
        ) or False
        return Response(data)
