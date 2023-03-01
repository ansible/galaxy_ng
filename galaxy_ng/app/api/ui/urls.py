from django.conf import settings
from django.urls import include, path
from rest_framework import routers

from galaxy_ng.app import constants

from . import views, viewsets

router = routers.SimpleRouter()
# TODO: Replace with a RedirectView
router.register('namespaces', viewsets.NamespaceViewSet, basename='namespaces')
router.register('my-namespaces', viewsets.MyNamespaceViewSet, basename='my-namespaces')
router.register('my-synclists', viewsets.MySyncListViewSet, basename='my-synclists')
router.register('users', viewsets.UserViewSet, basename='users')
router.register('collection-versions',
                viewsets.CollectionVersionViewSet, basename='collection-versions')
router.register(
    'imports/collections',
    viewsets.CollectionImportViewSet,
    basename='collection-imports',
)
router.register('tags', viewsets.TagsViewSet, basename='tags')
router.register('synclists', viewsets.SyncListViewSet, basename='synclists')
router.register('remotes', viewsets.CollectionRemoteViewSet, basename='remotes')
router.register('distributions', viewsets.DistributionViewSet, basename='distributions')
router.register('my-distributions', viewsets.MyDistributionViewSet, basename='my-distributions')

auth_views = [
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
]

container_paths = [
    path(
        "registries/<str:id>/",
        viewsets.ContainerRegistryRemoteViewSet.as_view(
            {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}
        ),
        name='execution-environments-registry-detail'),
    path(
        "registries/<str:id>/sync/",
        views.ContainerSyncRegistryView.as_view(),
        name='container-registry-sync'),
    path(
        "registries/<str:id>/index/",
        views.IndexRegistryEEView.as_view(),
        name='execution-environments-registry-index'),
    path(
        "registries/",
        viewsets.ContainerRegistryRemoteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='execution-environments-registry-list'),
    path(
        "remotes/<str:id>/",
        viewsets.ContainerRemoteViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='execution-environments-remote-detail'),
    path(
        "remotes/",
        viewsets.ContainerRemoteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='execution-environments-remote-list'),
]

# Groups are subclassed from pulpcore and use nested viewsets, so router.register
# unfortunately doesn't work
group_paths = [
    path(
        "",
        viewsets.GroupViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='groups'),
    path(
        "<str:pk>/",
        viewsets.GroupViewSet.as_view({'get': 'retrieve', 'delete': 'destroy'}),
        name='group-detail'),
    path(
        "<str:group_pk>/users/",
        viewsets.GroupUserViewSet.as_view({
            'get': 'list', 'post': 'create'}),
        name='group-model-permissions'),
    path(
        "<str:group_pk>/users/<str:pk>/",
        viewsets.GroupUserViewSet.as_view({
            'delete': 'destroy'}),
        name='group-model-permissions-detail'),
]

ai_index_paths = [
    # GET _ui/v1/ai_deny_index/
    path(
        "",
        views.AIDenyIndexListView.as_view(),
        name='ai-deny-index-list',
    ),
    # POST _ui/v1/ai_deny_index/{scope}/
    path(
        "<str:scope>/",
        views.AIDenyIndexAddView.as_view(),
        name='ai-deny-index-add',
    ),
    # DELETE _ui/v1/ai_deny_index/{scope}/{reference}/
    path(
        "<str:scope>/<str:reference>/",
        views.AIDenyIndexDetailView.as_view(),
        name='ai-deny-index-delete',
    )
]

signing_paths = [
    # _ui/v1/collection_signing/
    path(
        "",
        views.CollectionSignView.as_view(),
        name='collection-sign',
    ),
    # _ui/v1/collection_signing/staging/
    path(
        "<str:path>/",
        views.CollectionSignView.as_view(),
        name='collection-sign-repo',
    ),
    # _ui/v1/collection_signing/staging/namespace/
    path(
        "<str:path>/<str:namespace>/",
        views.CollectionSignView.as_view(),
        name='collection-sign-namespace',
    ),
    # _ui/v1/collection_signing/staging/namespace/collection/
    path(
        "<str:path>/<str:namespace>/<str:collection>/",
        views.CollectionSignView.as_view(),
        name='collection-sign-collection',
    ),
    # _ui/v1/collection_signing/staging/namespace/collection/1.0.0/
    path(
        "<str:path>/<str:namespace>/<str:collection>/<str:version>/",
        views.CollectionSignView.as_view(),
        name='collection-sign-version',
    ),
]

paths = [
    path('', include(router.urls)),

    path('auth/', include(auth_views)),
    path("settings/", views.SettingsView.as_view(), name="settings"),
    path("landing-page/", views.LandingPageView.as_view(), name="landing-page"),
    path('feature-flags/', views.FeatureFlagsView.as_view(), name='feature-flags'),
    path('controllers/', views.ControllerListView.as_view(), name='controllers'),
    path('groups/', include(group_paths)),
    path('collection_signing/', include(signing_paths)),
    path(
        'repo/<str:distro_base_path>/',
        viewsets.CollectionViewSet.as_view({'get': 'list'}),
        name='collections-list'
    ),
    path(
        'repo/<str:distro_base_path>/<str:namespace>/<str:name>/',
        viewsets.CollectionViewSet.as_view({'get': 'retrieve'}),
        name='collections-detail'
    ),
    # NOTE: Using path instead of SimpleRouter because SimpleRouter expects retrieve
    # to look up values with an ID
    path(
        'me/',
        viewsets.CurrentUserViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='me'
    ),
]

if settings.GALAXY_FEATURE_FLAGS['execution_environments']:
    paths.append(
        path('execution-environments/', include(container_paths)),
    )

if settings.GALAXY_FEATURE_FLAGS['ai_deny_index']:
    paths.append(
        path('ai_deny_index/', include(ai_index_paths)),
    )

app_name = "ui"

urlpatterns = [
    path('', viewsets.APIRootView.as_view({'get': 'list'}))
]

for version in constants.ALL_UI_API_VERSION:
    urlpatterns.append(path(
        constants.ALL_UI_API_VERSION[version],
        include((paths, app_name), namespace=version)
    ))
