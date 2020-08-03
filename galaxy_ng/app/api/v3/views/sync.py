from django.db import transaction
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.permissions import RestrictOnCloudDeployments


class SyncView(api_base.APIView):
    authentication_classes = (BasicAuthentication, *api_base.GALAXY_AUTHENTICATION_CLASSES)
    permission_classes = (IsAuthenticated, RestrictOnCloudDeployments)

    @transaction.atomic
    def post(self, request: Request, *args, **kwargs) -> Response:
        """Create and Spawn a SyncTask."""
        return Response({"task": "864d64d3-this-is-temp-data-fbe907bca76b"})


class SyncConfigView(api_base.APIView):
    authentication_classes = (BasicAuthentication, *api_base.GALAXY_AUTHENTICATION_CLASSES)
    permission_classes = (IsAuthenticated, RestrictOnCloudDeployments)

    def get(self, request: Request, *args, **kwargs) -> Response:
        """Retrieve Synchronization Config"""
        # TODO: Serialize this mocked data
        return Response(TMP_MOCK)

    @transaction.atomic
    def put(self, request: Request, *args, **kwargs) -> Response:
        """Update Synchronization Config."""
        # TODO: De-serialize this mocked data
        return Response(TMP_MOCK)


TMP_MOCK = {  # This is temporary while code is draft
    "name": "rh-certified",
    "url": "FQDN/automation-hub/v3/",
    "auth_url": "FQDN/auth/realms/redhat-external/protocol/openid-connect/token",
    "policy": "on-demand",
    "groups": [
        {"id": 1, "name": "admins"}
    ],
    "requirements_file": "",
    "updated_at": "..",
    "created_at": ".."
}
