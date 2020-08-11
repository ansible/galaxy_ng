
import logging

from pulp_ansible.app import viewsets as pulp_ansible_viewsets

from galaxy_ng.app.api.base import (
    LocalSettingsMixin,
)

log = logging.getLogger(__name__)


class GalaxyAnsibleRepositoryViewSet(LocalSettingsMixin,
                                     pulp_ansible_viewsets.AnsibleRepositoryViewSet):
    pass


class GalaxyAnsibleRepositoryVersionViewSet(LocalSettingsMixin,
                                            pulp_ansible_viewsets.RepositoryVersionViewSet):
    pass
