from django.urls import include, path
from rest_framework import routers
from pulp_ansible.app.urls import (
    v3_urls
)

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


    path("", include(v3_urls)),

    path("tasks/", viewsets.TaskViewSet.as_view({"get": "list"}), name="tasks-list"),
    path("tasks/<str:pk>/", viewsets.TaskViewSet.as_view({"get": "retrieve"}), name="tasks-detail"),
    path("excludes/", views.ExcludesView.as_view(), name="excludes-file"),
]
