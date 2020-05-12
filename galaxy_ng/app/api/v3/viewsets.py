import logging

from django.urls import reverse

from django.http import HttpResponseRedirect

from rest_framework.response import Response

from pulpcore.plugin.models import ContentArtifact
from pulp_ansible.app.galaxy.v3 import views as pulp_ansible_views

from galaxy_ng.app.api.base import LocalSettingsMixin, APIView
from .serializers import GalaxyNGCollectionVersionSerializer
# from galaxy_ng.app.common import metrics

# hmm, not sure what to do with this
# from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser


log = logging.getLogger(__name__)


class CollectionViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionViewSet):
    pass


class CollectionVersionViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionVersionViewSet):
    serializer_class = CollectionVersionSerializer

    # Custom retrive so we can use the class serializer_class GalaxyNGCollectionVersionSerializer
    # which is responsible for building the 'download_url'. The default pulp one doesn't
    # include the distro base_path which we need (https://pulp.plan.io/issues/6510)
    # so override this so we can use a different serializer
    def retrieve(self, request, *args, **kwargs):
        """
        Returns a CollectionVersion object.
        """
        instance = self.get_object()
        artifact = ContentArtifact.objects.get(content=instance)

        context = self.get_serializer_context()
        context["content_artifact"] = artifact

        serializer = self.get_serializer_class()(instance, context=context)
        return Response(serializer.data)


class CollectionImportViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionImportViewSet):
    pass


class CollectionUploadViewSet(LocalSettingsMixin, pulp_ansible_views.CollectionUploadViewSet):
    pass


class ApiRootView(APIView):
    def get(self, request, *args, **kwargs):
        data = {
            "location": "v3",
            "viewset": self.__class__.__name__,
            "distro_base_path": kwargs.get('path'),
            "available_versions": {"v3": "v3/"},
        }

        return Response(data)


class SlashApiRedirectPerDistroView(APIView):
    reverse_url = 'galaxy:api:root-per-distro'

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse(self.reverse_url), status=307)
