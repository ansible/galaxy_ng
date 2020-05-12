import logging

from django.conf import settings

from pulp_ansible.app.galaxy.v3.serializers import (
    CollectionVersionSerializer as _CollectionVersionSerializer
)

log = logging.getLogger(__name__)


class CollectionVersionSerializer(_CollectionVersionSerializer):
    def get_download_url(self, obj):
        """
        Get artifact download URL.
        """

        host = settings.CONTENT_ORIGIN.strip("/")
        prefix = settings.CONTENT_PATH_PREFIX.strip("/")
        distro_base_path = self.context["path"]
        filename_path = self.context["content_artifact"].relative_path.lstrip("/")

        download_url = f"{host}/{prefix}/{distro_base_path}/{filename_path}"

        return download_url
