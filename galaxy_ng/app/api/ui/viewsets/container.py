import logging

from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api.ui import serializers
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from galaxy_ng.app import models

log = logging.getLogger(__name__)


class CotainerDistributionViewSet(api_base.ModelViewSet):
    queryset = models.ContainerDistribution.objects.all()
    serializer_class = serializers.ContainerDistributionSerializer
    permission_classes = []

    def get_object(self):
        base_path = self.kwargs["name"]
        if self.kwargs.get("namespace"):
            base_path = "{}/{}".format(self.kwargs["namespace"], self.kwargs["name"])

        return get_object_or_404(self.queryset, base_path=base_path)
