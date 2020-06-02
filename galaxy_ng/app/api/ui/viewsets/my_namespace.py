
from galaxy_ng.app import models
from galaxy_ng.app.api import permissions
from .namespace import NamespaceViewSet


class MyNamespaceViewSet(NamespaceViewSet):
    def get_queryset(self):
        """
        Returns all namespaces for users in the partner-engineers group,
        otherwise returns namespaces with groups the user belongs to.
        """
        if permissions.IsPartnerEngineer().has_permission(self.request, self):
            return models.Namespace.objects.all()
        else:
            return models.Namespace.objects.filter(
                groups__in=self.request.user.groups.all()
            )
