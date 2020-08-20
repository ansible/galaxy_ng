from galaxy_ng.app import models
from guardian.shortcuts import get_objects_for_user
from galaxy_ng.app.access_control import access_policy
from .synclist import SyncListViewSet


class MySyncListViewSet(SyncListViewSet):
    permission_classes = [access_policy.MySyncListAccessPolicy, ]

    def get_queryset(self):
        """
        Returns all synclists for the user.
        """
        return get_objects_for_user(
            self.request.user,
            'galaxy.change_synclist',
            any_perm=True,
            klass=models.SyncList
        )
