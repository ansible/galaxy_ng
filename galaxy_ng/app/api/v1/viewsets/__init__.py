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
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRoleImportsViewSet
)

from .sync import (
    LegacyRolesSyncViewSet,
)


__all__ = (
    "LegacyNamespaceOwnersViewSet",
    "LegacyNamespaceProvidersViewSet",
    "LegacyNamespacesViewSet",
    "LegacyRoleContentViewSet",
    "LegacyRoleImportsViewSet",
    "LegacyRoleVersionsViewSet",
    "LegacyRolesSyncViewSet",
    "LegacyRolesViewSet",
    "LegacyUsersViewSet",
)
