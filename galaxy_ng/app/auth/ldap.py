import logging
from django_auth_ldap.backend import LDAPBackend, LDAPSettings
from galaxy_ng.app.models.auth import Group
from django.conf import settings


log = logging.getLogger(__name__)


class GalaxyLDAPSettings(LDAPSettings):

    _mirror_groups = None
    _cached_groups = None

    @property
    def MIRROR_GROUPS(self):
        log.debug("Cached LDAP groups: %s", str(self._cached_groups))
        if settings.get("GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS"):
            self._cached_groups = (
                self._cached_groups
                or set(Group.objects.all().values_list("name", flat=True))
            )
            if isinstance(self._mirror_groups, (set, frozenset)):
                return self._mirror_groups.union(self._cached_groups)
            else:
                return self._cached_groups

        return self._mirror_groups

    @MIRROR_GROUPS.setter
    def MIRROR_GROUPS(self, val):
        self._mirror_groups = val


class GalaxyLDAPBackend(LDAPBackend):
    """
    Add option to make mirror group only work with exiting groups in
    the db.
    """

    def __init__(self):
        self.settings = GalaxyLDAPSettings(self.settings_prefix, self.default_settings)
