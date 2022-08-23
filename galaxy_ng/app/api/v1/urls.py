from django.urls import path

from galaxy_ng.app.api.v1.views import LegacyRootView
from galaxy_ng.app.api.v1.viewsets import (
    LegacyRoleViewSet,
    LegacyRoleImportsViewSet,
    LegacyRoleContentViewSet,
    LegacyRoleVersionsViewSet,
    LegacyRolesViewSet,
    LegacyRolesSyncViewSet,
    # LegacyUserViewSet,
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
        'roles/<int:roleid>/',
        LegacyRoleViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name='legacy_role-detail'
    ),

    path(
        'roles/<int:roleid>/content/',
        LegacyRoleContentViewSet.as_view({"get": "retrieve"}),
        name='legacy_role-content'
    ),
    path(
        'roles/<int:roleid>/versions/',
        LegacyRoleVersionsViewSet.as_view({"get": "retrieve"}),
        name='legacy_role-versions'
    ),

    path(
        'search/roles/',
        LegacyRoleViewSet.as_view({"get": "list"}),
        name='legacy_role-search'
    ),

    path(
        'sync/',
        LegacyRolesSyncViewSet.as_view({"post": "create", "get": "get_task"}),
        name='legacy_role-sync'
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

    path('', LegacyRootView.as_view(), name='legacy-root')
]
