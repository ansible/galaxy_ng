import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from pulpcore.plugin.util import get_objects_for_user

from rest_framework.decorators import action

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy

from .synclist import SyncListViewSet

log = logging.getLogger(__name__)


class MySyncListViewSet(SyncListViewSet):
    permission_classes = [
        access_policy.MySyncListAccessPolicy,
    ]

    def get_queryset(self):
        """
        Returns all synclists for the user.
        """
        return get_objects_for_user(
            self.request.user,
            "galaxy.change_synclist",
            # any_perm=True,
            qs=models.SyncList.objects.all(),
        )

    # TODO: on UI click of synclist toggle the UI makes 2 calls
    # PUT /api/automation-hub/_ui/v1/my-synclists/1/
    # POST /api/automation-hub/_ui/v1/my-synclists/1/curate/
    # remove this method after UI stops calling curate action
    @action(detail=True, methods=["post"])
    def curate(self, request, pk):
        get_object_or_404(models.SyncList, pk=pk)
        return HttpResponse(status=202)
