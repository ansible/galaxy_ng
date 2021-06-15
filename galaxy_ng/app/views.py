from rest_framework import status as http_code
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet


class HealthViewSet(ViewSet):
    permission_classes = [AllowAny]

    def list(self, request):
        return Response(status=http_code.HTTP_200_OK)
