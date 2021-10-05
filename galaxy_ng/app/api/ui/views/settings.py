from django.conf import settings
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base


class SettingsView(api_base.APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        data = {}
        keyset = [
            "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS",
            "GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD",
            "GALAXY_FEATURE_FLAGS",
            "GALAXY_TOKEN_EXPIRATION",
        ]
        data = {key: settings.as_dict().get(key, None) for key in keyset}
        return Response(data)
