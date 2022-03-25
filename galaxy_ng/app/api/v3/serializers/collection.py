import logging
import mimetypes

from rest_framework import serializers
from rest_framework.exceptions import ValidationError, _get_error_details

from galaxy_ng.app.api.ui.serializers.base import Serializer
from galaxy_ng.app.api.utils import parse_collection_filename

log = logging.getLogger(__name__)


class CollectionUploadSerializer(Serializer):
    """
    A serializer for the Collection One Shot Upload API.
    """

    file = serializers.FileField(required=True)

    sha256 = serializers.CharField(required=False, default=None)

    class Meta():
        ref_name = "CollectionUploadWithDownloadUrlSerializer"

    def to_internal_value(self, data):
        """Parse and validate collection filename."""
        data = super().to_internal_value(data)

        errors = {}

        filename = data["file"].name

        try:
            filename_tuple = parse_collection_filename(filename)
        except ValueError as exc:
            errors['filename'] = _get_error_details(exc, default_code='invalid')
            log.error('CollectionUploadSerializer validation of filename failed: %s',
                      errors['filename'])
            raise ValidationError(errors)

        data.update({
            "filename": filename_tuple,
            "expected_namespace": filename_tuple.namespace,
            "expected_name": filename_tuple.name,
            "expected_version": filename_tuple.version,
            "mimetype": (mimetypes.guess_type(filename)[0] or 'application/octet-stream')
        })
        return data
