from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .base import Serializer


class CollectionSignSerializer(Serializer):
    """
    Describes the CollectionSignView payload for OPTIONS/metadata purposes only.

    CollectionSignView.post() parses request.data/view.kwargs manually and does
    not use this serializer for validation -- it exists solely so DRF's metadata
    machinery (SimpleMetadata.determine_actions) can generate field information
    for the 'POST' action in OPTIONS responses.
    """

    class Meta:
        pass

    signing_service = serializers.CharField()
    distro_base_path = serializers.CharField(
        required=False,
        help_text=_("Required if not provided via URL.")
    )
    namespace = serializers.CharField(
        required=False,
        help_text=_("Required if not provided via URL or content_units.")
    )
    collection = serializers.CharField(required=False)
    version = serializers.CharField(required=False)
    content_units = serializers.ListField(
        child=serializers.CharField(), required=False
    )
