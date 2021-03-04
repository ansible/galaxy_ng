import logging

import requests

from django.core.exceptions import ValidationError, ObjectDoesNotExist


from django.conf import settings
from django.http import HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse

from rest_framework.response import Response
from rest_framework.exceptions import APIException, NotFound

from pulpcore.plugin.models import Task
from pulpcore.plugin.tasking import enqueue_with_reservation
from pulp_ansible.app.galaxy.v3 import views as pulp_ansible_views
from pulp_ansible.app.models import CollectionVersion, AnsibleDistribution
from pulp_ansible.app.models import CollectionImport as PulpCollectionImport
from galaxy_ng.app.api import base as api_base

from galaxy_ng.app.constants import DeploymentMode, INBOUND_REPO_NAME_FORMAT
from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy

from galaxy_ng.app.api.v3.serializers import (
    CollectionSerializer,
    CollectionVersionSerializer,
    UnpaginatedCollectionVersionSerializer,
    CollectionVersionListSerializer,
    CollectionUploadSerializer,
)

from galaxy_ng.app.common import metrics
from galaxy_ng.app.tasks import (
    import_and_move_to_staging,
    import_and_auto_approve,
    call_copy_task,
    call_remove_task,
    curate_all_synclist_repository,
)

from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser


log = logging.getLogger(__name__)


class ViewNamespaceSerializerContextMixin:
    def get_serializer_context(self):
        """Inserts distribution path to a serializer context."""

        context = super().get_serializer_context()

        # view_namespace will be used by the serializers that need to return different hrefs
        # depending on where in the urlconf they are.
        # view_route is the url 'route' pattern, used to
        # handle the special case /api/automation-hub/v3/collections/ not having
        # a <str:path> in it's url
        request = context.get("request", None)
        context["view_namespace"] = None
        if request:
            context["view_namespace"] = request.resolver_match.namespace
            context["view_route"] = request.resolver_match.route

        return context


class RepoMetadataViewSet(api_base.LocalSettingsMixin,
                          pulp_ansible_views.RepoMetadataViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]


class UnpaginatedCollectionViewSet(api_base.LocalSettingsMixin,
                                   ViewNamespaceSerializerContextMixin,
                                   pulp_ansible_views.UnpaginatedCollectionViewSet):
    pagination_class = None
    permission_classes = [access_policy.CollectionAccessPolicy]
    serializer_class = CollectionSerializer


class CollectionViewSet(api_base.LocalSettingsMixin,
                        ViewNamespaceSerializerContextMixin,
                        pulp_ansible_views.CollectionViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]
    serializer_class = CollectionSerializer


class UnpaginatedCollectionVersionViewSet(api_base.LocalSettingsMixin,
                                          ViewNamespaceSerializerContextMixin,
                                          pulp_ansible_views.UnpaginatedCollectionVersionViewSet):
    pagination_class = None
    serializer_class = UnpaginatedCollectionVersionSerializer
    permission_classes = [access_policy.CollectionAccessPolicy]


class CollectionVersionViewSet(api_base.LocalSettingsMixin,
                               ViewNamespaceSerializerContextMixin,
                               pulp_ansible_views.CollectionVersionViewSet):
    serializer_class = CollectionVersionSerializer
    permission_classes = [access_policy.CollectionAccessPolicy]
    list_serializer_class = CollectionVersionListSerializer


class CollectionVersionDocsViewSet(api_base.LocalSettingsMixin,
                                   pulp_ansible_views.CollectionVersionDocsViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]


class CollectionImportViewSet(api_base.LocalSettingsMixin,
                              pulp_ansible_views.CollectionImportViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]


class CollectionUploadViewSet(api_base.LocalSettingsMixin,
                              pulp_ansible_views.CollectionUploadViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]
    parser_classes = [AnsibleGalaxy29MultiPartParser]
    serializer_class = CollectionUploadSerializer

    def _dispatch_import_collection_task(self, temp_file_pk, repository=None, **kwargs):
        """Dispatch a pulp task started on upload of collection version."""
        locks = []

        kwargs["temp_file_pk"] = temp_file_pk

        if repository:
            locks.append(repository)
            kwargs["repository_pk"] = repository.pk

        if settings.GALAXY_REQUIRE_CONTENT_APPROVAL:
            return enqueue_with_reservation(import_and_move_to_staging, locks, kwargs=kwargs)
        return enqueue_with_reservation(import_and_auto_approve, locks, kwargs=kwargs)

    # Wrap super().create() so we can create a galaxy_ng.app.models.CollectionImport based on the
    # the import task and the collection artifact details

    def _get_data(self, request):
        serializer = CollectionUploadSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        return serializer.validated_data

    @staticmethod
    def _get_path(kwargs, filename_ns):
        """Use path from '/content/<path>/v3/' or
           if user does not specify distribution base path
           then use an inbound distribution based on filename namespace.
        """
        path = kwargs['path']
        if kwargs.get('no_path_specified', None):
            path = INBOUND_REPO_NAME_FORMAT.format(namespace_name=filename_ns)
        return path

    @staticmethod
    def _check_path_matches_expected_repo(path, filename_ns):
        """Reject if path does not match expected inbound format
           containing filename namespace.

        Examples:
        Reject if path is "staging".
        Reject if path does not start with "inbound-".
        Reject if path is "inbound-alice" but filename namepace is "bob".
        """

        distro = get_object_or_404(AnsibleDistribution, base_path=path)
        repo_name = distro.repository.name
        if INBOUND_REPO_NAME_FORMAT.format(namespace_name=filename_ns) == repo_name:
            return
        raise NotFound(
            f'Path does not match: "{INBOUND_REPO_NAME_FORMAT.format(namespace_name=filename_ns)}"')

    def create(self, request, *args, **kwargs):
        data = self._get_data(request)
        filename = data['filename']

        path = self._get_path(kwargs, filename_ns=filename.namespace)

        try:
            namespace = models.Namespace.objects.get(name=filename.namespace)
        except models.Namespace.DoesNotExist:
            raise ValidationError(
                'Namespace "{0}" does not exist.'.format(filename.namespace)
            )

        self._check_path_matches_expected_repo(path, filename_ns=namespace.name)

        self.check_object_permissions(request, namespace)

        try:
            response = super(CollectionUploadViewSet, self).create(request, path)
        except ValidationError:
            log.exception('Failed to publish artifact %s (namespace=%s, sha256=%s)',  # noqa
                          data['file'].name, namespace, data.get('sha256'))
            raise

        task_href = response.data['task']

        # icky, have to extract task id from the task_href url
        task_id = task_href.strip("/").split("/")[-1]

        task_detail = Task.objects.get(pk=task_id)

        pulp_collection_import = PulpCollectionImport.objects.get(pk=task_id)

        models.CollectionImport.objects.create(
            task_id=pulp_collection_import,
            created_at=task_detail.pulp_created,
            namespace=namespace,
            name=data['filename'].name,
            version=data['filename'].version,
        )

        # TODO: CollectionImport.get_absolute_url() should be able to generate this, but
        #       it needs the  repo/distro base_path for the <path> part of url
        import_obj_url = reverse("galaxy:api:content:v3:collection-import",
                                 kwargs={'pk': str(task_detail.pulp_id),
                                         'path': path})

        log.debug('import_obj_url: %s', import_obj_url)
        return Response(
            data={'task': import_obj_url},
            status=response.status_code
        )


class CollectionArtifactDownloadView(api_base.APIView):
    permission_classes = [access_policy.CollectionAccessPolicy]
    action = 'retrieve'

    def get(self, request, *args, **kwargs):
        metrics.collection_artifact_download_attempts.inc()

        url = 'http://{host}:{port}/{prefix}/{distro_base_path}/{filename}'.format(
            host=settings.X_PULP_CONTENT_HOST,
            port=settings.X_PULP_CONTENT_PORT,
            prefix=settings.CONTENT_PATH_PREFIX.strip('/'),
            distro_base_path=self.kwargs['path'],
            filename=self.kwargs['filename'],
        )

        response = requests.get(url, stream=True, allow_redirects=False)

        if response.status_code == requests.codes.not_found:
            metrics.collection_artifact_download_failures.labels(
                status=requests.codes.not_found
            ).inc()
            raise NotFound()

        if response.status_code == requests.codes.found:
            return HttpResponseRedirect(response.headers['Location'])

        if response.status_code == requests.codes.ok:
            metrics.collection_artifact_download_successes.inc()

            return StreamingHttpResponse(
                response.raw.stream(amt=4096),
                content_type=response.headers['Content-Type']
            )

        metrics.collection_artifact_download_failures.labels(status=response.status_code).inc()
        raise APIException('Unexpected response from content app. '
                           f'Code: {response.status_code}.')


class CollectionVersionMoveViewSet(api_base.ViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]

    def move_content(self, request, *args, **kwargs):
        """Remove content from source repo and add to destination repo.

        Creates new RepositoryVersion of source repo without content included.
        Creates new RepositoryVersion of destination repo with content included.
        """

        version_str = '-'.join([self.kwargs[key] for key in ('namespace', 'name', 'version')])
        try:
            collection_version = CollectionVersion.objects.get(
                namespace=self.kwargs['namespace'],
                name=self.kwargs['name'],
                version=self.kwargs['version'],
            )
        except ObjectDoesNotExist:
            raise NotFound(f'Collection {version_str} not found')

        try:
            src_repo = AnsibleDistribution.objects.get(
                base_path=self.kwargs['source_path']).repository
            dest_repo = AnsibleDistribution.objects.get(
                base_path=self.kwargs['dest_path']).repository
        except ObjectDoesNotExist:
            raise NotFound(f'Repo(s) for moving collection {version_str} not found')

        src_versions = CollectionVersion.objects.filter(pk__in=src_repo.latest_version().content)
        if collection_version not in src_versions:
            raise NotFound(f'Collection {version_str} not found in source repo')

        dest_versions = CollectionVersion.objects.filter(pk__in=dest_repo.latest_version().content)
        if collection_version in dest_versions:
            raise NotFound(f'Collection {version_str} already found in destination repo')

        copy_task = call_copy_task(collection_version, src_repo, dest_repo)
        remove_task = call_remove_task(collection_version, src_repo)

        curate_task_id = None
        if settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.INSIGHTS.value:
            golden_repo = AnsibleDistribution.objects.get(
                base_path=settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
            ).repository

            if dest_repo == golden_repo or src_repo == golden_repo:
                repo_name = golden_repo.name
                locks = [golden_repo]
                task_args = (repo_name,)
                task_kwargs = {}

                curate_task = enqueue_with_reservation(
                    curate_all_synclist_repository, locks, args=task_args, kwargs=task_kwargs
                )
                curate_task_id = curate_task.id

        return Response(
            data={
                'copy_task_id': copy_task.id,
                'remove_task_id': remove_task.id,
                "curate_all_synclist_repository_task_id": curate_task_id,
            },
            status='202'
        )
