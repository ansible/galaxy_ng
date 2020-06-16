from django.urls import include, path

from rest_framework import routers

from . import views
from . import viewsets

router = routers.SimpleRouter()
router.register('namespaces', viewsets.NamespaceViewSet, basename='namespaces')

namespace_urls = [
    path("", include(router.urls)),
]

auth_urls = [
    path("auth/token/", views.TokenView.as_view(), name="auth-token"),
]


urlpatterns = [
    path(
        'collections/',
        viewsets.CollectionViewSet.as_view({'get': 'list'}),
        name='collections-list'
    ),
    path(
        'collections/<str:namespace>/<str:name>/',
        viewsets.CollectionViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='collections-detail'
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/',
        viewsets.CollectionVersionViewSet.as_view({'get': 'list'}),
        name='collection-versions-list',
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/<str:version>/',
        viewsets.CollectionVersionViewSet.as_view({'get': 'retrieve'}),
        name='collection-versions-detail',
    ),
    path(
        'imports/collections/<str:pk>/',
        viewsets.CollectionImportViewSet.as_view({'get': 'retrieve'}),
        name='collection-import',
    ),
    path(
        'artifacts/collections/',
        viewsets.CollectionUploadViewSet.as_view({'post': 'create'}),
        name='collection-artifact-upload'
    ),
    path(
        'artifacts/collections/<str:path>/<str:filename>',
        viewsets.CollectionArtifactDownloadView.as_view(),
        name='collection-artifact-download'
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/<str:version>/move/'
        '<str:source_path>/<str:dest_path>/',
        viewsets.CollectionVersionMoveViewSet.as_view({'post': 'move_content'}),
        name='collection-version-move',
    ),
]
