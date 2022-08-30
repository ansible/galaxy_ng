from .namespaces import (
    LegacyNamespacesViewSet,
    LegacyUsersViewSet
)

from .roles import (
    LegacyRolesViewSet,
    LegacyRoleViewSet,
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRoleImportsViewSet
)

from .sync import (
    LegacyRolesSyncViewSet,
)


__all__ = (
    LegacyNamespacesViewSet,
    LegacyUsersViewSet,
    LegacyRolesViewSet,
    LegacyRolesSyncViewSet,
    LegacyRoleViewSet,
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRoleImportsViewSet,
)
