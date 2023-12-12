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
    LegacyNamespaceProvidersViewSet,
    LegacyUsersViewSet
)

from galaxy_ng.app.api.v1.viewsets import (
    CollectionSurveyRollupList,
    CollectionSurveyList,
    LegacyRoleSurveyRollupList,
    LegacyRoleSurveyList,
)


urlpatterns = [
    path(
        'imports',
        LegacyRoleImportsViewSet.as_view({"get": "list", "post": "create"}),
        name='legacy_role-imports-no-trailing-slash'
    ),
    path(
        'imports/',
        LegacyRoleImportsViewSet.as_view({"get": "list", "post": "create"}),
        name='legacy_role-imports'
    ),
    path(
        'imports/<int:pk>/',
        LegacyRoleImportsViewSet.as_view({"get": "retrieve"}),
        name='legacy_role-import'
    ),

    path(
        'removerole/',
        LegacyRolesViewSet.as_view({"delete": "delete_by_url_params"}),
        name='legacy_role-remove'
    ),

    path(
        'roles/',
        LegacyRolesViewSet.as_view({"list": "list", "get": "list"}),
        name='legacy_role-list'
    ),

    path(
        'roles/<int:pk>/',
        LegacyRolesViewSet.as_view({"get": "retrieve", "delete": "destroy", "put": "update"}),
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
        LegacyNamespacesViewSet.as_view({"get": "list", "post": "create"}),
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
    path(
        'namespaces/<int:pk>/providers/',
        LegacyNamespaceProvidersViewSet.as_view({"get": "list", "put": "update", "post": "update"}),
        name='legacy_namespace_providers-list'
    ),

    path(
        "scores/collections/",
        CollectionSurveyRollupList.as_view({'get': 'list'}),
        name='collection-survey-rollup-list'
    ),
    path(
        "scores/collections/<str:namespace>/<str:name>/",
        CollectionSurveyRollupList.as_view({'get': 'retrieve_collection'}),
        name='collection-survey-rollup-list-by-fqn'
    ),
    path(
        "scores/roles/",
        LegacyRoleSurveyRollupList.as_view({'get': 'list'}),
        name='legacyrole-survey-rollup-list'
    ),

    path(
        "surveys/collections/",
        CollectionSurveyList.as_view({'get': 'list'}),
        name='collection-survey-list'
    ),
    path(
        "surveys/collections/<str:namespace>/<str:name>/",
        CollectionSurveyList.as_view({'post': 'create'}),
        name='collection-survey-create1'
    ),
    path(
        "surveys/collections/<str:pk>/",
        CollectionSurveyList.as_view({'post': 'create'}),
        name='collection-survey-create2'
    ),
    path(
        "surveys/roles/",
        LegacyRoleSurveyList.as_view({'get': 'list'}),
        name='legacyrole-survey-list'
    ),
    path(
        "surveys/roles/<int:id>/",
        LegacyRoleSurveyList.as_view({'post': 'create'}),
        name='legacyrole-survey-create'
    ),

    path('', LegacyRootView.as_view(), name='legacy-root')
]
