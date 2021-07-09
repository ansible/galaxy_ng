import yaml
from django.core.exceptions import ObjectDoesNotExist
from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from pulp_ansible.app.models import AnsibleDistribution
from rest_framework.renderers import (
    BaseRenderer,
    BrowsableAPIRenderer,
    JSONRenderer
)
from rest_framework.request import Request
from rest_framework.response import Response
from yaml.dumper import SafeDumper


def get_synclist_excludes(base_path):
    """Get Synclist from distro base_path"""
    try:
        repo = AnsibleDistribution.objects.get(base_path=base_path).repository
        synclist = models.SyncList.objects.get(repository=repo, policy="exclude")
        return synclist.collections.all()
    except ObjectDoesNotExist:
        return None


def serialize_collection_queryset(queryset):
    """Serialize a Queryset in to a JSONable format."""
    return queryset is not None and [
        {
            "name": "{collection.namespace}.{collection.name}".format(collection=collection)
        }
        for collection in queryset.all()
    ] or []


class RequirementsFileRenderer(BaseRenderer):
    """Renders requirements YAML format."""

    media_type = 'application/yaml'
    format = 'yaml'
    charset = 'utf-8'
    encoder = SafeDumper

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """
        Renders data to YAML.

        Args:
            data: Object to be rendered as YAML.
            accepted_media_type: The media type the client accepts.
            renderer_context: Renderer context.

        Returns:
            A rendered response in YAML format.
        """
        if data is None:
            return ""

        return yaml.dump(
            data,
            stream=None,
            encoding=self.charset,
            Dumper=self.encoder,
            allow_unicode=True,
            default_flow_style=False,
        )


class ExcludesView(api_base.APIView):
    permission_classes = [access_policy.CollectionAccessPolicy]
    action = 'list'
    renderer_classes = [
        JSONRenderer,
        BrowsableAPIRenderer,
        RequirementsFileRenderer
    ]

    def get(self, request: Request, *args, **kwargs):
        """
        Returns a list of excludes for a given distro.
        """
        queryset = get_synclist_excludes(self.kwargs["path"])
        collections_to_exclude = serialize_collection_queryset(queryset)
        return Response({"collections": collections_to_exclude})
