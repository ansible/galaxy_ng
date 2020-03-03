"""API v3 URLs Configuration."""

from django.urls import path

from . import viewsets


app_name = "v3"
urlpatterns = [
    path(
        'collections/',
        viewsets.CollectionViewSet.as_view({'get': 'list'}),
    ),
    path(
        'collections/<str:namespace>/<str:name>/',
        viewsets.CollectionViewSet.as_view({'get': 'retrieve', 'put': 'update'}),
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/',
        viewsets.CollectionVersionViewSet.as_view({'get': 'list'}),
    ),
    path(
        'collections/<str:namespace>/<str:name>/versions/<str:version>/',
        viewsets.CollectionVersionViewSet.as_view({'get': 'retrieve'}),
    ),
    path(
        'imports/collections/<str:pk>/',
        viewsets.CollectionImportViewSet.as_view({'get': 'retrieve'}),
        name='collection-imports',
    ),
    path(
        'artifacts/collections/',
        viewsets.CollectionArtifactUploadView.as_view(),
    ),
    path(
        'artifacts/collections/<str:filename>',
        viewsets.CollectionArtifactDownloadView.as_view(),
    ),
]
