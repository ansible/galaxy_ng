from galaxy_ng.app import models
from pulpcore.plugin.util import get_objects_for_user

from .namespace import NamespaceViewSet


class MyNamespaceViewSet(NamespaceViewSet):
    def get_queryset(self):
        return get_objects_for_user(
            self.request.user,
            ('galaxy.change_namespace', 'galaxy.upload_to_namespace'),
            any_perm=True,
            qs=models.Namespace.objects.all()
        )
