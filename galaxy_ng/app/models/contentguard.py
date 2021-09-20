from rest_framework.exceptions import APIException
from pulpcore.plugin.models import ContentGuard


class CollectionDownloadContentGuard(ContentGuard):
    """
    A content guard that protects content based on user authentication
    """

    def permit(self, request):
        """
        Authorize the specified request based on if the request is authenticated.
        """
        from galaxy_ng.app.api.v3.viewsets import CollectionArtifactDownloadView

        view = CollectionArtifactDownloadView()
        setattr(view, "get_object", lambda: self)
        setattr(view, "action", "download")
        try:
            view.check_permissions(request)
        except APIException as e:
            raise PermissionError(e)

    class Meta:
        default_related_name = "%(app_label)s_%(model_name)s"
