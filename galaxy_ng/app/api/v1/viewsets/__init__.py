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


__all__ = (
    "LegacyNamespacesViewSet",
    "LegacyNamespaceOwnersViewSet",
    "LegacyNamespaceProvidersViewSet",
    "LegacyUsersViewSet",
    "LegacyRolesViewSet",
    "LegacyRoleContentViewSet",
    "LegacyRoleVersionsViewSet",
    "LegacyRoleImportsViewSet",
)
