import logging

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers
from django.shortcuts import get_object_or_404
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app import models

log = logging.getLogger(__name__)


class CotainerRepositoryViewSet(api_base.ModelViewSet):
    queryset = models.ContainerDistribution.objects.all()
    serializer_class = serializers.ContainerRepositorySerializer

    permission_classes = [access_policy.ContainerRepositoryAccessPolicy]

    def get_object(self):
        base_path = self.kwargs["name"]
        if self.kwargs.get("namespace"):
            base_path = "{}/{}".format(self.kwargs["namespace"], self.kwargs["name"])

        print(base_path)
        return get_object_or_404(self.queryset, base_path=base_path)
