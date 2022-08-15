from django.conf import settings
from django.urls import include, path, re_path
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

container_repo_paths = [
    path(
        'images/',
        viewsets.ContainerRepositoryManifestViewSet.as_view({'get': 'list'}),
        name='container-repository-images'),
    path(
        'images/<str:manifest_ref>/',
        viewsets.ContainerRepositoryManifestViewSet.as_view(
            {"get": "retrieve", "delete": "destroy"}
        ),
        name='container-repository-images-config-blob'),
    path(
        'history/',
        viewsets.ContainerRepositoryHistoryViewSet.as_view({'get': 'list'}),
        name='container-repository-history'),
    path(
        'readme/',
        viewsets.ContainerReadmeViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='container-repository-readme'),
    path(
        'tags/',
        viewsets.ContainerTagViewset.as_view({'get': 'list'}),
        name='container-repository-tags'),
    path(
        "sync/",
        views.ContainerSyncRemoteView.as_view(),
        name='container-repository-sync'),
]

container_paths = [
    path(
        "repositories/",
        viewsets.ContainerRepositoryViewSet.as_view({'get': 'list'}),
        name='container-repository-list'),
    path(
        "namespaces/<str:name>/",
        viewsets.ContainerNamespaceViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='container-namespace-detail'),
    path(
        "namespaces/",
        viewsets.ContainerNamespaceViewSet.as_view({'get': 'list'}),
        name='container-namespace-list'),
    path(
        "registries/<str:pk>/",
        viewsets.ContainerRegistryRemoteViewSet.as_view(
            {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}
        ),
        name='execution-environments-registry-detail'),
    path(
        "registries/<str:pk>/sync/",
        views.ContainerSyncRegistryView.as_view(),
        name='container-registry-sync'),
    path(
        "registries/<str:pk>/index/",
        views.IndexRegistryEEView.as_view(),
        name='execution-environments-registry-index'),
    path(
        "registries/",
        viewsets.ContainerRegistryRemoteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='execution-environments-registry-list'),
    path(
        "remotes/<str:pk>/",
        viewsets.ContainerRemoteViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='execution-environments-remote-detail'),
    path(
        "remotes/",
        viewsets.ContainerRemoteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='execution-environments-remote-list'),

    # image names can't start with _, so namespacing all the nested views
    # under _content prevents cases where an image could be named foo/images
    # and conflict with our URL paths.
    re_path(
        r'repositories/(?P<base_path>[-\w.]+\/{0,1}[-\w.]+)/_content/',
        include(container_repo_paths)),

    # This regex can capture "namespace/name" and "name"
    re_path(
        r"repositories/(?P<base_path>[-\w.]+\/{0,1}[-\w.]+)/",
        viewsets.ContainerRepositoryViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="container-repository-detail",
    ),
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

app_name = "ui"

urlpatterns = [
    path('', viewsets.APIRootView.as_view({'get': 'list'}))
]

for version in constants.ALL_UI_API_VERSION:
    urlpatterns.append(path(
        constants.ALL_UI_API_VERSION[version],
        include((paths, app_name), namespace=version)
    ))
