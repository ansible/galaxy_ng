from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from galaxy_ng.app.api import base as api_base


API_PATH_PREFIX = settings.GALAXY_API_PATH_PREFIX.strip("/")


class LegacyRootView(api_base.APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({
            'sync': f'/{API_PATH_PREFIX}/v1/sync/',
            'imports': f'/{API_PATH_PREFIX}/v1/imports/',
            'roles': f'/{API_PATH_PREFIX}/v1/roles/',
            'users': f'/{API_PATH_PREFIX}/v1/users/',
            'namespaces': f'/{API_PATH_PREFIX}/v1/namespaces/'
        })
