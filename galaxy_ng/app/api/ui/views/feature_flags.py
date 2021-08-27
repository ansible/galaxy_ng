from django.conf import settings
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base


class FeatureFlagsView(api_base.APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        return Response(settings.GALAXY_FEATURE_FLAGS)
