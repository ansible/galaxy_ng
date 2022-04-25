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
    # >>>> OVERRIDDEN PULP ANSIBLE ENDPOINTS <<<<<

    # Some pulp ansible endpoints have to be overridden because we have special logic
    # that is specific to galaxy_ng's business needs. Until
    # https://github.com/pulp/pulp_ansible/issues/835 is resolved, the only solution
    # we have for this problem is to just override the viewset. Overridden API endpoints
    # should be put here. Please include comments that describe why the override is necesary.
    # Overridding an endpoint should be a measure of last resort.

    # Disable the unpaginated collection views
    # The following endpoints are related to issue https://issues.redhat.com/browse/AAH-224
    # For now endpoints are temporary deactivated
    path(
        "collections/all/",
        views.NotFoundView.as_view(),
        name="legacy-v3-metadata-collection-list",
    ),
    path(
        "collection_versions/all/",
        views.NotFoundView.as_view(),
        name="legacy-v3-metadata-collection-versions-list",
    ),

    # At the moment Automation Hub on console.redhat.com has a nonstandard configuration
    # for collection download as well as prometheus metrics that are used to track the
    # health of the service. Until https://issues.redhat.com/browse/AAH-1385 can be resolved
    # we need to continue providing this endpoint from galaxy_ng.
    path(
        "plugin/ansible/content/<path:distro_base_path>/collections/artifacts/<str:filename>",
        viewsets.CollectionArtifactDownloadView.as_view(),
        name="collection-artifact-download",
    ),

    # Overridden because the galaxy_ng endpoints only allow collections to be uploaded into
    # specific repositories.
    path(
        "artifacts/collections/",
        viewsets.CollectionUploadViewSet.as_view({"post": "create"}),
        name="collection-artifact-upload",
    ),

    # This is the same endpoint as `artifacts/collections/`. It can't be redirected because
    # redirects break on collection publish.
    path(
        "plugin/ansible/content/<path:distro_base_path>/collections/artifacts/",
        viewsets.CollectionUploadViewSet.as_view({"post": "create"}),
        name="collection-artifact-upload",
    ),

    # >>>> END OVERRIDDEN PULP ANSIBLE ENDPOINTS <<<<<

    # TODO: Endpoints that have not been moved to pulp ansible yet
    path(
        "collections/<str:namespace>/<str:name>/versions/<str:version>/move/"
        "<str:source_path>/<str:dest_path>/",
        viewsets.CollectionVersionMoveViewSet.as_view({"post": "move_content"}),
        name="collection-version-move",
    ),

    path("", include(v3_urls)),

    path("tasks/", viewsets.TaskViewSet.as_view({"get": "list"}), name="tasks-list"),
    path("tasks/<str:pk>/", viewsets.TaskViewSet.as_view({"get": "retrieve"}), name="tasks-detail"),
    path("excludes/", views.ExcludesView.as_view(), name="excludes-file"),
]
