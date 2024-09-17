import logging
from django_auth_ldap.backend import LDAPBackend, LDAPSettings
from galaxy_ng.app.models.auth import Group, User
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


class PrefixedLDAPBackend(GalaxyLDAPBackend):

    @property
    def prefix(self):
        return settings.get("RENAMED_USERNAME_PREFIX")

    def authenticate(self, *args, **kwargs):
        """
        When a prefixed user authenticates, remove the prefix from their
        username kwarg and treat them as the non-prefixed user.
        """
        if username := kwargs.get("username"):
            if username.startswith(self.prefix):
                kwargs["username"] = username.removeprefix(self.prefix)
                return super().authenticate(*args, **kwargs)

        return super().authenticate(*args, **kwargs)

    def get_or_build_user(self, username, ldap_user):
        """
        If the username is not prefixed but a prefixed user exists in the system,
        return that preifxed user. Otherwise, treat the un-prefixed username as
        the source of truth and continue on with get_or_build.
        """
        if (
            not username.startswith(self.prefix)
            and User.objects.filter(username=self.prefix + username)
        ):
            return super().get_or_build_user(self.prefix + username, ldap_user)

        return super().get_or_build_user(username, ldap_user)
