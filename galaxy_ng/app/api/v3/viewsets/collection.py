import logging

import requests
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema
from pulp_ansible.app.galaxy.v3 import views as pulp_ansible_views
from pulp_ansible.app.models import AnsibleDistribution
from pulp_ansible.app.models import CollectionImport as PulpCollectionImport
from pulp_ansible.app.models import CollectionVersion

from pulpcore.plugin.models import Content
from pulpcore.plugin.models import SigningService
from pulpcore.plugin.models import Task
from pulpcore.plugin.serializers import AsyncOperationResponseSerializer
from pulpcore.plugin.tasking import dispatch
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3.serializers import CollectionUploadSerializer
from galaxy_ng.app.common import metrics
from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser
from galaxy_ng.app.constants import INBOUND_REPO_NAME_FORMAT, DeploymentMode
from galaxy_ng.app.tasks import (
    call_move_content_task,
    call_sign_and_move_task,
    import_and_auto_approve,
    import_and_move_to_staging,
)


log = logging.getLogger(__name__)


class CollectionUploadViewSet(api_base.LocalSettingsMixin,
                              pulp_ansible_views.CollectionUploadViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]
    parser_classes = [AnsibleGalaxy29MultiPartParser]
    serializer_class = CollectionUploadSerializer

    def _dispatch_import_collection_task(self, temp_file_pk, repository=None, **kwargs):
        """Dispatch a pulp task started on upload of collection version."""
        locks = []
        context = super().get_serializer_context()
        request = context.get("request", None)

        kwargs["temp_file_pk"] = temp_file_pk
        kwargs["username"] = request.user.username

        if repository:
            locks.append(repository)
            kwargs["repository_pk"] = repository.pk

        if settings.GALAXY_REQUIRE_CONTENT_APPROVAL:
            return dispatch(import_and_move_to_staging, exclusive_resources=locks, kwargs=kwargs)
        return dispatch(import_and_auto_approve, exclusive_resources=locks, kwargs=kwargs)

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

        # the legacy collection upload views don't get redirected and still have to use the
        # old path arg
        path = kwargs.get(
            'distro_base_path',
            kwargs.get('path', settings.ANSIBLE_DEFAULT_DISTRIBUTION_PATH)
        )

        if path == settings.ANSIBLE_DEFAULT_DISTRIBUTION_PATH:
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
            _('Path does not match: "%s"')
            % INBOUND_REPO_NAME_FORMAT.format(namespace_name=filename_ns)
        )

    @extend_schema(
        description="Create an artifact and trigger an asynchronous task to create "
        "Collection content from it.",
        summary="Upload a collection",
        request=CollectionUploadSerializer,
        responses={202: AsyncOperationResponseSerializer},
    )
    def create(self, request, *args, **kwargs):
        data = self._get_data(request)
        filename = data['filename']

        path = self._get_path(kwargs, filename_ns=filename.namespace)

        try:
            namespace = models.Namespace.objects.get(name=filename.namespace)
        except models.Namespace.DoesNotExist:
            raise ValidationError(
                _('Namespace "{0}" does not exist.').format(filename.namespace)
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
        import_obj_url = reverse("galaxy:api:v3:collection-imports-detail",
                                 kwargs={'pk': str(task_detail.pk),
                                         'path': path})

        log.debug('import_obj_url: %s', import_obj_url)
        return Response(
            data={'task': import_obj_url},
            status=response.status_code
        )


class CollectionArtifactDownloadView(api_base.APIView):
    permission_classes = [access_policy.CollectionAccessPolicy]
    action = 'download'

    def _get_tcp_response(self, url):
        return requests.get(url, stream=True, allow_redirects=False)

    def _get_ansible_distribution(self, base_path):
        return AnsibleDistribution.objects.get(base_path=base_path)

    def get(self, request, *args, **kwargs):
        metrics.collection_artifact_download_attempts.inc()

        distro_base_path = self.kwargs['distro_base_path']
        filename = self.kwargs['filename']
        prefix = settings.CONTENT_PATH_PREFIX.strip('/')
        distribution = self._get_ansible_distribution(distro_base_path)

        if settings.ANSIBLE_COLLECT_DOWNLOAD_LOG:
            pulp_ansible_views.CollectionArtifactDownloadView.log_download(
                request, filename, distro_base_path
            )

        if settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.INSIGHTS.value:
            url = 'http://{host}:{port}/{prefix}/{distro_base_path}/{filename}'.format(
                host=settings.X_PULP_CONTENT_HOST,
                port=settings.X_PULP_CONTENT_PORT,
                prefix=prefix,
                distro_base_path=distro_base_path,
                filename=filename,
            )
            response = self._get_tcp_response(
                distribution.content_guard.cast().preauthenticate_url(url)
            )

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
            raise APIException(
                _('Unexpected response from content app. Code: %s.') % response.status_code
            )
        elif settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.STANDALONE.value:
            url = '{host}/{prefix}/{distro_base_path}/{filename}'.format(
                host=settings.CONTENT_ORIGIN.strip("/"),
                prefix=prefix,
                distro_base_path=distro_base_path,
                filename=filename,
            )
            return redirect(distribution.content_guard.cast().preauthenticate_url(url))


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
            raise NotFound(_('Collection %s not found') % version_str)

        try:
            src_repo = AnsibleDistribution.objects.get(
                base_path=self.kwargs['source_path']).repository
            dest_repo = AnsibleDistribution.objects.get(
                base_path=self.kwargs['dest_path']).repository
        except ObjectDoesNotExist:
            raise NotFound(_('Repo(s) for moving collection %s not found') % version_str)

        content_obj = Content.objects.get(pk=collection_version.pk)

        if content_obj not in src_repo.latest_version().content:
            raise NotFound(_('Collection %s not found in source repo') % version_str)

        if content_obj in dest_repo.latest_version().content:
            raise NotFound(_('Collection %s already found in destination repo') % version_str)

        response_data = {
            "copy_task_id": None,
            "remove_task_id": None,
            # Can be removed once all synclist stuff is remove
            # and client compat isnt a concern -akl
            "curate_all_synclist_repository_task_id": None,
        }
        golden_repo = settings.get("GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH", "published")
        auto_sign = settings.get("GALAXY_AUTO_SIGN_COLLECTIONS", False)
        move_task_params = {
            "collection_version": collection_version,
            "source_repo": src_repo,
            "dest_repo": dest_repo,
        }

        if auto_sign and dest_repo.name == golden_repo:
            # Assumed that if user has access to modify the repo, they can also sign the content
            # so we don't need to check access policies here.
            signing_service_name = settings.get(
                "GALAXY_COLLECTION_SIGNING_SERVICE", "ansible-default"
            )
            try:
                signing_service = SigningService.objects.get(name=signing_service_name)
            except ObjectDoesNotExist:
                raise NotFound(_('Signing %s service not found') % signing_service_name)

            move_task = call_sign_and_move_task(signing_service, **move_task_params)
        else:
            require_signatures = settings.get("GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL", False)
            if dest_repo.name == golden_repo and require_signatures:
                if collection_version.signatures.count() == 0:
                    return Response(
                        {
                            "detail": _(
                                "Collection {namespace}.{name} could not be approved "
                                "because system requires at least a signature for approval."
                            ).format(
                                namespace=collection_version.namespace,
                                name=collection_version.name,
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            move_task = call_move_content_task(**move_task_params)

        response_data['copy_task_id'] = response_data['remove_task_id'] = move_task.pk

        if settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.INSIGHTS.value:
            golden_repo = AnsibleDistribution.objects.get(
                base_path=settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
            ).repository

        return Response(data=response_data, status='202')
