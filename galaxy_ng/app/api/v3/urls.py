from django.conf import settings
from django.urls import include, path, re_path
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

plugin_paths = [

    # At the moment Automation Hub on console.redhat.com has a nonstandard configuration
    # for collection download as well as prometheus metrics that are used to track the
    # health of the service. Until https://issues.redhat.com/browse/AAH-1385 can be resolved
    # we need to continue providing this endpoint from galaxy_ng.
    path(
        "ansible/content/<path:distro_base_path>/collections/artifacts/<str:filename>",
        viewsets.CollectionArtifactDownloadView.as_view(),
        name="collection-artifact-download",
    ),

    # This is the same endpoint as `artifacts/collections/`. It can't be redirected because
    # redirects break on collection publish.
    path(
        "ansible/content/<path:distro_base_path>/collections/artifacts/",
        viewsets.CollectionUploadViewSet.as_view({"post": "create"}),
        name="collection-artifact-upload",
    ),
]

if settings.GALAXY_FEATURE_FLAGS['execution_environments']:
    plugin_paths.append(
        path('execution-environments/', include(container_paths)),
    )

urlpatterns = [
    # >>>> OVERRIDDEN PULP ANSIBLE ENDPOINTS <<<<<

    # Some pulp ansible endpoints have to be overridden because we have special logic
    # that is specific to galaxy_ng's business needs. Until
    # https://github.com/pulp/pulp_ansible/issues/835 is resolved, the only solution
    # we have for this problem is to just override the viewset. Overridden API endpoints
    # should be put here. Please include comments that describe why the override is necesary.
    # Overridding an endpoint should be a measure of last resort.

    path("plugin/", include(plugin_paths)),

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
    path(
        "collections/<str:namespace>/<str:name>/versions/<str:version>/copy/"
        "<str:source_path>/<str:dest_path>/",
        viewsets.CollectionVersionCopyViewSet.as_view({"post": "copy_content"}),
        name="collection-version-copy",
    ),

    path("", include(v3_urls)),

    path("tasks/", viewsets.TaskViewSet.as_view({"get": "list"}), name="tasks-list"),
    path("tasks/<str:pk>/", viewsets.TaskViewSet.as_view({"get": "retrieve"}), name="tasks-detail"),
    path("excludes/", views.ExcludesView.as_view(), name="excludes-file"),
]
