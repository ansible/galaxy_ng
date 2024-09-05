import logging

from galaxy_ng.app.api.v3.viewsets.namespace import NamespaceViewSet
from galaxy_ng.app.api.ui.v1 import versioning

log = logging.getLogger(__name__)


class NamespaceViewSet(NamespaceViewSet):
    versioning_class = versioning.UIVersioning
