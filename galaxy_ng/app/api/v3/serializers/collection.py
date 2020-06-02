import logging
import mimetypes

from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ValidationError, _get_error_details

from galaxy_ng.app.api.ui.serializers.base import Serializer
from galaxy_ng.app.api.utils import parse_collection_filename

from pulp_ansible.app.galaxy.v3.serializers import (
    CollectionVersionSerializer as _CollectionVersionSerializer
)

log = logging.getLogger(__name__)


class CollectionVersionSerializer(_CollectionVersionSerializer):
    def get_download_url(self, obj):
        """
        Get artifact download URL.
        """

        host = settings.CONTENT_ORIGIN.strip("/")
        prefix = settings.CONTENT_PATH_PREFIX.strip("/")
        distro_base_path = self.context["path"]
        filename_path = self.context["content_artifact"].relative_path.lstrip("/")

        download_url = f"{host}/{prefix}/{distro_base_path}/{filename_path}"

        return download_url

    class Meta(_CollectionVersionSerializer.Meta):
        ref_name = "CollectionVersionWithDownloadUrlSerializer"


class CollectionUploadSerializer(Serializer):
    """
    A serializer for the Collection One Shot Upload API.
    """

    file = serializers.FileField(required=True)

    sha256 = serializers.CharField(required=False, default=None)

    def to_internal_value(self, data):
        """Parse and validate collection filename."""
        data = super().to_internal_value(data)

        errors = {}

        filename = data["file"].name

        try:
            filename_tuple = parse_collection_filename(filename)
        except ValueError as exc:
            errors['filename'] = _get_error_details(exc)
            log.error('CollectionUploadSerializer validation of filename failed: %s',
                      errors['filename'])
            raise ValidationError(errors)

        data.update({
            "filename": filename_tuple,
            "mimetype": (mimetypes.guess_type(filename)[0] or 'application/octet-stream')
        })
        return data
