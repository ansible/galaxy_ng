from django.conf import settings
from django.urls import path, include, re_path
from rest_framework import routers

from galaxy_ng.app import constants

from . import views
from . import viewsets


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
        viewsets.ContainerRepositoryManifestViewSet.as_view({'get': 'retrieve'}),
        name='container-repository-images-config-blob'),
    path(
        'history/',
        viewsets.ContainerRepositoryHistoryViewSet.as_view({'get': 'list'}),
        name='container-repository-history'),
    path(
        'readme/',
        viewsets.ContainerReadmeViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='container-repository-readme'),
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

    # image names can't start with _, so namespacing all the nested views
    # under _content prevents cases where an image could be named foo/images
    # and conflict with our URL paths.
    re_path(
        r'repositories/(?P<base_path>[-\w]+\/{0,1}[-\w]+)/_content/',
        include(container_repo_paths)),

    # This regex can capture "namespace/name" and "name"
    re_path(
        r'repositories/(?P<base_path>[-\w]+\/{0,1}[-\w]+)/',
        viewsets.ContainerRepositoryViewSet.as_view({'get': 'retrieve'}),
        name='container-repository-detail'),
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
        "<str:group_pk>/model-permissions/",
        viewsets.GroupModelPermissionViewSet.as_view({
            'get': 'list', 'post': 'create'}),
        name='group-model-permissions'),
    path(
        "<str:group_pk>/model-permissions/<str:pk>/",
        viewsets.GroupModelPermissionViewSet.as_view({
            'get': 'retrieve', 'delete': 'destroy'}),
        name='group-model-permissions-detail'),
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

paths = [
    path('', include(router.urls)),

    path('auth/', include(auth_views)),
    path('feature-flags/', views.FeatureFlagsView.as_view(), name='feature-flags'),
    path('groups/', include(group_paths)),
    path(
        'repo/<str:path>/',
        viewsets.CollectionViewSet.as_view({'get': 'list'}),
        name='collections-list'
    ),
    path(
        'repo/<str:path>/<str:namespace>/<str:name>/',
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
