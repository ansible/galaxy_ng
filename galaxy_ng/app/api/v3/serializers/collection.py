import logging
import mimetypes

from django.conf import settings

from rest_framework import serializers
from rest_framework.exceptions import ValidationError, _get_error_details
from rest_framework.reverse import reverse

from galaxy_ng.app.api.ui.serializers.base import Serializer
from galaxy_ng.app.api.utils import parse_collection_filename

from pulp_ansible.app.galaxy.v3.serializers import (
    CollectionSerializer as _CollectionSerializer,
    CollectionRefSerializer as _CollectionRefSerializer,
    CollectionVersionSerializer as _CollectionVersionSerializer,
    CollectionVersionListSerializer as _CollectionVersionListSerializer,
)

log = logging.getLogger(__name__)


class HrefNamespaceMixin:
    def _get_href(self, url_name, **kwargs):
        """Generic get_*_href that uses context["view_namespace"] to reverse the right url"""

        view_namespace = self.context["view_namespace"]

        # Handle the case where the /api/automation-hub/v3/collections/  urls do not
        # include a "<str:path>" path param. ie, the bacwares compatible default "golden" repo
        if "/<str:path>/v3/" not in self.context["view_route"]:
            del kwargs["path"]

        return reverse(
            f"{view_namespace}:{url_name}",
            kwargs=kwargs,
        )


class CollectionSerializer(_CollectionSerializer, HrefNamespaceMixin):
    class Meta(_CollectionSerializer.Meta):
        ref_name = "CollectionWithFixedHrefsSerializer"

    def get_href(self, obj):
        """Get href."""
        kwargs = {"path": self.context["path"], "namespace": obj.namespace, "name": obj.name}
        return self._get_href("collections-detail", **kwargs)

    def get_versions_url(self, obj):
        """Get a link to a collection versions list."""
        kwargs = {"path": self.context["path"], "namespace": obj.namespace, "name": obj.name}
        return self._get_href("collection-versions-list", **kwargs)

    def get_highest_version(self, obj):
        """Get a highest version and its link."""
        collection = self.context["highest_versions"][obj.pk]
        kwargs = {
            "path": self.context["path"],
            "namespace": collection.namespace,
            "name": collection.name,
            "version": collection.version,
        }
        href = self._get_href("collection-versions-detail", **kwargs)
        return {"href": href, "version": str(collection.version)}


class CollectionRefSerializer(_CollectionRefSerializer, HrefNamespaceMixin):
    class Meta:
        ref_name = "CollectionWithFixedHrefsRefSerializer"

    def get_href(self, obj):
        """Returns link to a collection."""

        kwargs = {"path": self.context["path"], "namespace": obj.namespace, "name": obj.name}
        return self._get_href("collections-detail", **kwargs)


class CollectionVersionListSerializer(_CollectionVersionListSerializer, HrefNamespaceMixin):
    class Meta(_CollectionVersionListSerializer.Meta):
        ref_name = "CollectionVersionWithFixedHrefsRefListSerializer"

    def get_href(self, obj):
        """Get href."""
        kwargs = {
            "path": self.context["path"],
            "namespace": obj.namespace,
            "name": obj.name,
            "version": obj.version,
        }

        return self._get_href("collection-versions-detail", **kwargs)


class CollectionVersionSerializer(_CollectionVersionSerializer, HrefNamespaceMixin):

    collection = CollectionRefSerializer(read_only=True)

    class Meta(_CollectionVersionSerializer.Meta):
        ref_name = "CollectionVersionWithDownloadUrlSerializer"

    def get_download_url(self, obj):
        """
        Get artifact download URL.
        """

        host = settings.ANSIBLE_API_HOSTNAME.strip("/")
        prefix = settings.GALAXY_API_PATH_PREFIX.strip("/")
        distro_base_path = self.context["path"]
        return f"{host}/{prefix}/v3/artifacts/collections/{distro_base_path}/{obj.relative_path}"

    def get_href(self, obj):
        """Get href."""
        kwargs = {"path": self.context["path"], "namespace": obj.namespace,
                  "name": obj.name, "version": obj.version}
        return self._get_href("collection-versions-detail", **kwargs)


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
