
from django.urls import path

from . import viewsets

app_name = "v3"
urlpatterns = [
    path(
        'collections/',
        viewsets.CollectionViewSet.as_view({'get': 'list'}),
        name='collection-list'
    ),
    path(
        'collections/<str:namespace>/<str:name>/',
        viewsets.CollectionViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
        name='collection'
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/',
        viewsets.CollectionVersionViewSet.as_view({'get': 'list'}),
        name='collection-version-list',
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/<str:version>/',
        viewsets.CollectionVersionViewSet.as_view({'get': 'retrieve'}),
        name='collection-version',
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
        '',
        viewsets.ApiRootView.as_view(),
        # name='root-v3',
    ),
]
