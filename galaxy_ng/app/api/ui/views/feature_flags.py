from django.conf import settings
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from pulpcore.plugin.models import SigningService
from galaxy_ng.app.api import base as api_base


class FeatureFlagsView(api_base.APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        flags = settings.get("GALAXY_FEATURE_FLAGS", {})
        _load_conditional_signing_flags(flags)
        return Response(flags)


def _load_conditional_signing_flags(flags):
    """Computes conditional flags for signing feature. ref: AAH-1690"""
    # kept for backwards compatibility to avoid breaking outdated UIs
    flags.setdefault(
        "collection_signing",
        bool(settings.get("GALAXY_COLLECTION_SIGNING_SERVICE"))
    )

    # Main signing feature switcher (replaces collection_signing)
    enabled = flags.setdefault(
        "signatures_enabled",
        flags["collection_signing"]
    )
    # Should UI require signature upload for enabling approval button?
    require_upload = flags.setdefault(
        "require_upload_signatures",
        enabled and bool(settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL"))
    )

    # Is the system configured with a Signing Service to create signatures?
    def _signing_service_exists(settings):
        name = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")
        return SigningService.objects.filter(name=name).exists()

    can_create = flags.setdefault(
        "can_create_signatures",
        enabled and _signing_service_exists(settings)
    )

    # Is the system enabled to accept signature uploads?
    can_upload = flags.setdefault(
        "can_upload_signatures",
        enabled and require_upload or bool(settings.get("GALAXY_SIGNATURE_UPLOAD_ENABLED"))
    )
    # Does the system automatically sign automatically upon approval?
    flags.setdefault(
        "collection_auto_sign",
        enabled and can_create and bool(settings.get("GALAXY_AUTO_SIGN_COLLECTIONS"))
    )

    # Should UI show badges, text, signature blob, filters...
    flags.setdefault("display_signatures", enabled and can_create or can_upload)
