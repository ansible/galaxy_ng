from django.contrib import auth as django_auth
from django.db import transaction
from django.http import Http404

from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status as http_code

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.permissions import RestrictOnCloudDeployments
from galaxy_ng.app.api.ui.serializers import LoginSerializer


__all__ = (
    'LoginView',
    'LogoutView',
    'TokenView',
)


class LoginView(api_base.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = (RestrictOnCloudDeployments,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        user = django_auth.authenticate(request, username=username, password=password)
        if user is None:
            return Response(status=http_code.HTTP_403_FORBIDDEN)

        django_auth.login(request, user)
        return Response(status=http_code.HTTP_204_NO_CONTENT)


class LogoutView(api_base.APIView):
    permission_classes = (RestrictOnCloudDeployments,)

    def post(self, request, *args, **kwargs):
        django_auth.logout(request)
        return Response(status=http_code.HTTP_204_NO_CONTENT)


class TokenView(api_base.APIView):
    permission_classes = (IsAuthenticated, RestrictOnCloudDeployments)

    def get(self, request, *args, **kwargs):
        try:
            token = Token.objects.get(user=self.request.user)
        except Token.DoesNotExist:
            raise Http404()
        return Response({'token': token.key})

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """Create or refresh user token."""
        Token.objects.filter(user=self.request.user).delete()
        token = Token.objects.create(user=self.request.user)
        return Response({'token': token.key})

    def delete(self, request, *args, **kwargs):
        """Invalidate user token."""
        Token.objects.filter(user=self.request.user).delete()
        return Response(status=http_code.HTTP_204_NO_CONTENT)
