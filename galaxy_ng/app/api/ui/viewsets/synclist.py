import logging

from galaxy_ng.app import models
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app.api import permissions


log = logging.getLogger(__name__)


class SyncListViewSet(api_base.ModelViewSet):
    queryset = models.SyncList.objects.all()
    serializer_class = serializers.SyncListSerializer

    def get_permissions(self):
        return super().get_permissions() + \
            [permissions.IsPartnerEngineer(),
             permissions.RestrictOnStandaloneDeployments()]
