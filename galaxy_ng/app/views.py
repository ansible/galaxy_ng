from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.conf import settings
from galaxy_ng.app.api import base as api_base

from rest_framework.settings import api_settings
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, APIException

import drf_spectacular.views
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

import json
import os


def health_view(request):
    return HttpResponse('OK')


class HttpResponsePermanentRedirect308(HttpResponsePermanentRedirect):
    status_code = 308


class PulpAPIRedirectView(api_base.APIView):
    permission_classes = []

    def get(self, request, api_path):
        url = f"/{settings.API_ROOT.strip('/')}/api/{api_path.strip('/')}/"

        args = request.META.get("QUERY_STRING", "")
        if args:
            url = f"{url}?{args}"

        # Returning 308 instead of 302 since 308 requires that clients maintain the
        # same method as the original request.
        return HttpResponsePermanentRedirect308(url)


class ApiSpecRequireAuthMixin:
    """
    Control authentication with GALAXY_API_SPEC_REQUIRE_AUTHENTICATION
    apply to galaxy_ng openapi endpoints and monkey-patch pulp openapi endpoints.
    """
    def get_permissions(self):
        if settings.get("GALAXY_API_SPEC_REQUIRE_AUTHENTICATION"):
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_authenticators(self):
        """overwrite permissions for pulp endpoints before monkey-patching."""
        return [cls() for cls in api_settings.DEFAULT_AUTHENTICATION_CLASSES]


class ProtectedSpectacularJSONAPIView(ApiSpecRequireAuthMixin, SpectacularJSONAPIView):
    pass


class ProtectedSpectacularYAMLAPIView(ApiSpecRequireAuthMixin, SpectacularYAMLAPIView):
    pass


class ProtectedSpectacularRedocView(ApiSpecRequireAuthMixin, SpectacularRedocView):
    pass


class ProtectedSpectacularSwaggerView(ApiSpecRequireAuthMixin, SpectacularSwaggerView):
    pass


class StaticOpenAPIView(ApiSpecRequireAuthMixin, api_base.APIView):
    """
    Serves the static OpenAPI specification from galaxy_ng/app/static/galaxy.json
    Uses ApiSpecRequireAuthMixin to respect GALAXY_API_SPEC_REQUIRE_AUTHENTICATION setting
    """
    def get(self, request, *args, **kwargs):
        # Path to the static galaxy.json file
        static_file_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'app',
            'static',
            'galaxy.json'
        )

        if not os.path.exists(static_file_path):
            raise NotFound("OpenAPI specification file not found")

        try:
            with open(static_file_path) as f:
                openapi_spec = json.load(f)
        except json.JSONDecodeError:
            raise APIException("Invalid JSON in OpenAPI specification file")

        return Response(openapi_spec)


drf_spectacular.views.SpectacularJSONAPIView = ProtectedSpectacularJSONAPIView
drf_spectacular.views.SpectacularYAMLAPIView = ProtectedSpectacularYAMLAPIView
drf_spectacular.views.SpectacularRedocView = ProtectedSpectacularRedocView
drf_spectacular.views.SpectacularSwaggerView = ProtectedSpectacularSwaggerView
