from django.urls import include, path
from rest_framework import routers

from . import views, viewsets

router = routers.SimpleRouter()
router.register('namespaces', viewsets.NamespaceViewSet, basename='namespaces')

namespace_urls = [
    path("", include(router.urls)),
]

auth_urls = [
    path("auth/token/", views.TokenView.as_view(), name="auth-token"),
]

# these are included in the base router so that they only appear under `content/<distro>/v3`
sync_urls = [
    path(
        "sync/",
        views.SyncRemoteView.as_view(),
        name='sync'
    ),
    path(
        "sync/config/",
        viewsets.SyncConfigViewSet.as_view({"get": "retrieve", "put": "update"}),
        name="sync-config",
    ),
]

urlpatterns = [
    # The following endpoints are related to issue https://issues.redhat.com/browse/AAH-224
    # For now endpoints are temporary deactivated
    #
    # path("", viewsets.RepoMetadataViewSet.as_view({"get": "retrieve"}), name="repo-metadata"),
    # path(
    #     "collections/all/",
    #     viewsets.UnpaginatedCollectionViewSet.as_view({"get": "list"}),
    #     name="all-collections-list",
    # ),
    # path(
    #     "collection_versions/all/",
    #     viewsets.UnpaginatedCollectionVersionViewSet.as_view({"get": "list"}),
    #     name="all-collection-versions-list",
    # ),
    path(
        "collections/", viewsets.CollectionViewSet.as_view({"get": "list"}), name="collections-list"
    ),
    path(
        "collections/<str:namespace>/<str:name>/",
        viewsets.CollectionViewSet.as_view(
            {"get": "retrieve", "patch": "update", "delete": "destroy"}
        ),
        name="collections-detail",
    ),
    path(
        "collections/<str:namespace>/<str:name>/versions/",
        viewsets.CollectionVersionViewSet.as_view({"get": "list"}),
        name="collection-versions-list",
    ),
    path(
        "collections/<str:namespace>/<str:name>/versions/<str:version>/",
        viewsets.CollectionVersionViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="collection-versions-detail",
    ),
    path(
        "collections/<str:namespace>/<str:name>/versions/<str:version>/docs-blob/",
        viewsets.CollectionVersionDocsViewSet.as_view({"get": "retrieve"}),
        name="collection-versions-detail-docs",
    ),
    path(
        "imports/collections/<str:pk>/",
        viewsets.CollectionImportViewSet.as_view({"get": "retrieve"}),
        name="collection-import",
    ),
    path(
        "artifacts/collections/",
        viewsets.CollectionUploadViewSet.as_view({"post": "create"}),
        name="collection-artifact-upload",
    ),
    path(
        "artifacts/collections/<str:path>/<str:filename>",
        viewsets.CollectionArtifactDownloadView.as_view(),
        name="collection-artifact-download",
    ),
    path(
        "collections/<str:namespace>/<str:name>/versions/<str:version>/move/"
        "<str:source_path>/<str:dest_path>/",
        viewsets.CollectionVersionMoveViewSet.as_view({"post": "move_content"}),
        name="collection-version-move",
    ),
    path("tasks/", viewsets.TaskViewSet.as_view({"get": "list"}), name="tasks-list"),
    path("tasks/<str:pk>/", viewsets.TaskViewSet.as_view({"get": "retrieve"}), name="tasks-detail"),
    path("excludes/", views.ExcludesView.as_view(), name="excludes-file"),
]
