import json

from django.core import exceptions
from django.shortcuts import get_object_or_404

from rest_framework.response import Response
from pulp_container.app import models as container_models

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy


# Using a view instead of a viewset since this endpoint effectively loads a
# json blob from disk instead of being tied to a specific model.
class ContainerConfigBlobView(api_base.GenericAPIView):
    permission_classes = []

    def get(self, request, *args, **kwargs):
        # manifest_ref can be a tag name or a manifest digest
        manifest_ref = kwargs['manifest_ref']
        base_path = kwargs['base_path']
        repo = get_object_or_404(
            container_models.ContainerDistribution, base_path=base_path).repository.latest_version()
        config_blob = None

        try:
            # try loading a tag with the manifest_ref
            # TODO: Fix this with get_content in pulpcore 3.11
            tag_content = repo.content.filter(pulp_type='container.tag')
            tag = container_models.Tag.objects.filter(
                pk__in=tag_content).get(name=manifest_ref)
            config_blob = tag.tagged_manifest.config_blob
        except exceptions.ObjectDoesNotExist:
            # TODO: Fix this with get_content in pulpcore 3.11
            manifest_content = repo.content.filter(pulp_type='container.manifest')
            manifest = get_object_or_404(
                container_models.Manifest.objects.filter(
                    pk__in=manifest_content), digest=manifest_ref)
            config_blob = manifest.config_blob

        with config_blob._artifacts.first().file.open() as f:
            config_json = json.load(f)

        return Response(config_json)
