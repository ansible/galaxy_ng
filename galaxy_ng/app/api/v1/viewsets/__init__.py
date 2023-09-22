from .namespaces import (
    LegacyNamespacesViewSet,
    LegacyNamespaceOwnersViewSet,
    LegacyNamespaceProvidersViewSet,
)

from .users import (
    LegacyUsersViewSet
)

from .roles import (
    LegacyRolesViewSet,
    # LegacyRoleViewSet,
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRoleImportsViewSet
)

from .sync import (
    LegacyRolesSyncViewSet,
)


__all__ = (
    LegacyNamespacesViewSet,
    LegacyNamespaceOwnersViewSet,
    LegacyNamespaceProvidersViewSet,
    LegacyUsersViewSet,
    LegacyRolesViewSet,
    LegacyRolesSyncViewSet,
    # LegacyRoleViewSet,
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRoleImportsViewSet,
)
