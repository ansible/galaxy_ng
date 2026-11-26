import json
import logging
import os
from enum import StrEnum

import drf_spectacular.views
from django.conf import settings
from django.db import DatabaseError
from django.http import HttpResponse, HttpResponsePermanentRedirect
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularYAMLAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from pulpcore.app.models.status import AppStatus
from pulpcore.app.views.status import StatusView as PulpStatusView
from rest_framework import status as http_status
from rest_framework.exceptions import NotFound, APIException
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.settings import api_settings

from galaxy_ng.app.api import base as api_base

logger = logging.getLogger(__name__)


class ReadinessStatus(StrEnum):
    GOOD = "good"
    DEGRADED = "degraded"
    FAILED = "failed"


class ReadinessIssue(StrEnum):
    DATABASE_UNAVAILABLE = "database_unavailable"
    REDIS_UNAVAILABLE = "redis_unavailable"
    APP_STATUS_CHECK_FAILED = "app_status_check_failed"
    API_APPS_UNAVAILABLE = "api_apps_unavailable"
    WORKERS_UNAVAILABLE = "workers_unavailable"
    CONTENT_APPS_UNAVAILABLE = "content_apps_unavailable"


READINESS_HTTP_STATUS_CODES = {
    ReadinessStatus.GOOD: http_status.HTTP_200_OK,
    ReadinessStatus.DEGRADED: http_status.HTTP_200_OK,
    ReadinessStatus.FAILED: http_status.HTTP_500_INTERNAL_SERVER_ERROR,
}


def status_response(
    readiness_status: ReadinessStatus,
    *issues: ReadinessIssue,
) -> Response:
    data = {
        "status": readiness_status.value,
        "issues": [issue.value for issue in issues],
    }

    return Response(data, status=READINESS_HTTP_STATUS_CODES[readiness_status])


def health_view(request):
    return HttpResponse('OK')


class StatusViewSet(api_base.ViewSet):
    """Provide a concise status summary for readiness checks."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def list(self, request):
        if not PulpStatusView._get_db_conn_status():
            return status_response(
                ReadinessStatus.FAILED,
                ReadinessIssue.DATABASE_UNAVAILABLE,
            )

        issues = []
        if settings.CACHE_ENABLED and not PulpStatusView._get_redis_conn_status():
            issues.append(ReadinessIssue.REDIS_UNAVAILABLE)

        try:
            online_apps = AppStatus.objects.online()
            api_apps_available = online_apps.filter(app_type="api").exists()
            workers_available = online_apps.filter(app_type="worker").exists()
            content_apps_available = online_apps.filter(app_type="content").exists()
        except DatabaseError:
            logger.exception("Database error while checking online app status")
            return status_response(
                ReadinessStatus.FAILED,
                ReadinessIssue.DATABASE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Failed to check online API apps, workers, and content apps")
            return status_response(
                ReadinessStatus.FAILED,
                ReadinessIssue.APP_STATUS_CHECK_FAILED,
            )

        if not api_apps_available:
            issues.append(ReadinessIssue.API_APPS_UNAVAILABLE)
        if not workers_available:
            issues.append(ReadinessIssue.WORKERS_UNAVAILABLE)
        if not content_apps_available:
            issues.append(ReadinessIssue.CONTENT_APPS_UNAVAILABLE)

        if issues:
            return status_response(ReadinessStatus.DEGRADED, *issues)

        return status_response(ReadinessStatus.GOOD)


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
