from django.conf import settings
from django.utils.translation import gettext_lazy as _
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
    _messages = []

    signing_service_name = settings.get("GALAXY_COLLECTION_SIGNING_SERVICE")

    # kept for backwards compatibility to avoid breaking outdated UIs
    flags.setdefault("collection_signing", bool(signing_service_name))

    # Should UI require signature upload for enabling approval button?
    require_upload = flags.setdefault(
        "require_upload_signatures", bool(settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL"))
    )

    # Main signing feature switcher (replaces collection_signing)
    # If system requires signature upload, then assume signing is enabled
    # also if signing service name is set, assume signing is enabled
    enabled = flags.setdefault("signatures_enabled", require_upload or flags["collection_signing"])

    # Is the system enabled to accept signature uploads?
    can_upload = flags.setdefault(
        "can_upload_signatures",
        enabled and require_upload or bool(settings.get("GALAXY_SIGNATURE_UPLOAD_ENABLED"))
    )

    # Is the system configured with a Signing Service to create signatures?
    signing_service_exists = False
    if signing_service_name:
        signing_service_exists = SigningService.objects.filter(name=signing_service_name).exists()
        if not signing_service_exists:
            msg = _(
                "WARNING:GALAXY_COLLECTION_SIGNING_SERVICE is set to '{}', "
                "however the respective SigningService does not exist in the database."
            )
            _messages.append(msg.format(signing_service_name))

    can_create = flags.setdefault("can_create_signatures", enabled and signing_service_exists)

    # Does the system automatically sign automatically upon approval?
    auto_sign = flags.setdefault(
        "collection_auto_sign",
        enabled and can_create and bool(settings.get("GALAXY_AUTO_SIGN_COLLECTIONS"))
    )

    if auto_sign and not signing_service_exists:
        msg = _(
            "WARNING:GALAXY_AUTO_SIGN_COLLECTIONS is set to True, "
            "however the system is not configured with a SigningService to create signatures."
        )
        _messages.append(msg)

    # Should UI show badges, text, signature blob, filters...
    can_display = flags.setdefault("display_signatures", enabled and any((can_create, can_upload)))

    # Is system displaying only synced signatures?
    if can_display and not any((can_create, can_upload)):
        msg = _(
            "INFO:System is configured to display signatures (coming from remote syncs) "
            "but is not configured to create or accept upload of signatures."
        )
        _messages.append(msg)

    # Container Signing
    execution_environments_enabled = flags.get("execution_environments", False)
    container_signing_service_name = settings.get("GALAXY_CONTAINER_SIGNING_SERVICE")

    # Is the system configured with a Signing Service for containers?
    container_signing_service_exists = False
    if container_signing_service_name:
        container_signing_service_exists = SigningService.objects.filter(
            name=container_signing_service_name
        ).exists()
        if not container_signing_service_exists:
            msg = _(
                "WARNING:GALAXY_CONTAINER_SIGNING_SERVICE is set to '{}', "
                "however the respective SigningService does not exist in the database."
            )
            _messages.append(msg.format(container_signing_service_name))

    # This allows users to export GALAXY_FEATURE_FLAGS__container_signing=false|true
    container_signing_enabled = flags.setdefault(
        "container_signing", container_signing_service_exists
    )

    # Is the system with a Signing Service for containers enabled but EEs disabled?
    if container_signing_enabled and not execution_environments_enabled:
        msg = _(
            "WARNING: container_signing is enabled via '{}' SigningService, "
            "however execution environments are disabled on the system."
        )
        _messages.append(msg.format(container_signing_service_name))

    # Display messages if any
    flags["_messages"] = _messages
