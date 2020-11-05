import logging

from guardian.shortcuts import get_objects_for_user

from rest_framework.decorators import action

from pulpcore.plugin.viewsets import OperationPostponedResponse
from pulpcore.plugin.tasking import enqueue_with_reservation

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.tasks import curate_synclist_repository

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
            any_perm=True,
            accept_global_perms=False,
            klass=models.SyncList,
        )

    @action(detail=True, methods=["post"])
    def curate(self, request, pk=None):
        locks = [pk]
        task_args = (pk,)
        task_kwargs = {}

        synclist_task = enqueue_with_reservation(
            curate_synclist_repository, locks, args=task_args, kwargs=task_kwargs
        )

        log.debug("synclist_task: %s", synclist_task)

        return OperationPostponedResponse(synclist_task, request)
