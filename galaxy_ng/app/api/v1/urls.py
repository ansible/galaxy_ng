from django.urls import path

from galaxy_ng.app.api.v1.views import LegacyRootView
from galaxy_ng.app.api.v1.viewsets import (
    # LegacyRoleViewSet,
    LegacyRoleImportsViewSet,
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRolesViewSet,
    LegacyRolesSyncViewSet,
    LegacyNamespacesViewSet,
    LegacyNamespaceOwnersViewSet,
    LegacyUsersViewSet
)


urlpatterns = [
    path(
        'imports/',
        LegacyRoleImportsViewSet.as_view({"post": "create", "get": "get_task"}),
        name='legacy_role-imports'
    ),

    path(
        'roles/',
        LegacyRolesViewSet.as_view({"list": "list", "get": "list"}),
        name='legacy_role-list'
    ),

    path(
        'roles/<int:pk>/',
        LegacyRolesViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name='legacy_role-detail'
    ),

    path(
        'roles/<int:pk>/content/',
        LegacyRoleContentViewSet.as_view({"get": "retrieve"}),
        name='legacy_role-content'
    ),
    path(
        'roles/<int:pk>/versions/',
        LegacyRoleVersionsViewSet.as_view({"get": "retrieve"}),
        name='legacy_role-versions'
    ),

    path(
        'search/roles/',
        LegacyRolesViewSet.as_view({"get": "list"}),
        name='legacy_role-search'
    ),

    path(
        'sync/',
        LegacyRolesSyncViewSet.as_view({"post": "create"}),
        name='legacy_role-sync'
    ),

    path(
        'sync/<int:id>/',
        LegacyRolesSyncViewSet.as_view({"get": "get_task"}),
        name='legacy_role-sync-task'
    ),

    path(
        'tasks/<int:id>/',
        LegacyRoleImportsViewSet.as_view({"get": "get_task"}),
        name='legacy_role-imports'
    ),

    path(
        'users/',
        LegacyUsersViewSet.as_view({"get": "list"}),
        name='legacy_users-userlist'
    ),
    path(
        'users/<int:pk>/',
        LegacyUsersViewSet.as_view({"get": "retrieve"}),
        name='legacy_user-userdetail'
    ),
    path(
        'namespaces/',
        LegacyNamespacesViewSet.as_view({"get": "list"}),
        name='legacy_namespace-list'
    ),
    path(
        'namespaces/<int:pk>/',
        LegacyNamespacesViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name='legacy_namespace-detail'
    ),
    path(
        'namespaces/<int:pk>/owners/',
        LegacyNamespaceOwnersViewSet.as_view({"get": "list", "put": "update"}),
        name='legacy_namespace_owners-list'
    ),

    path('', LegacyRootView.as_view(), name='legacy-root')
]
