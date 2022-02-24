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
from pulpcore.plugin.viewsets import OperationPostponedResponse
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from semantic_version import SimpleSpec, Version

from galaxy_ng.app import models
from galaxy_ng.app.access_control import access_policy
from galaxy_ng.app.api import base as api_base
from galaxy_ng.app.api.v3.serializers import (
    CollectionSerializer,
    CollectionUploadSerializer,
    CollectionVersionListSerializer,
    CollectionVersionSerializer,
    UnpaginatedCollectionVersionSerializer,
)
from galaxy_ng.app.common import metrics
from galaxy_ng.app.common.parsers import AnsibleGalaxy29MultiPartParser
from galaxy_ng.app.constants import INBOUND_REPO_NAME_FORMAT, DeploymentMode
from galaxy_ng.app.tasks import (
    call_move_content_task,
    curate_all_synclist_repository,
    call_sign_and_move_task,
    call_sign_task,
    delete_collection,
    delete_collection_version,
    import_and_auto_approve,
    import_and_move_to_staging,
)


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


def get_collection_dependents(parent):
    """Given a parent collection, return a list of collection versions that depend on it."""
    key = f"{parent.namespace}.{parent.name}"
    dependents = []
    for child in CollectionVersion.objects.exclude(collection=parent).filter(
        dependencies__has_key=key
    ):
        dependents.append(child)
    return dependents


class CollectionViewSet(api_base.LocalSettingsMixin,
                        ViewNamespaceSerializerContextMixin,
                        pulp_ansible_views.CollectionViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]
    serializer_class = CollectionSerializer

    @extend_schema(
        description="Trigger an asynchronous delete task",
        responses={status.HTTP_202_ACCEPTED: AsyncOperationResponseSerializer},
    )
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Allow a Collection to be deleted.
        1. Perform Dependency Check to verify that each CollectionVersion
           inside Collection can be deleted
        2. If the Collection can’t be deleted, return the reason why
        3. If it can, dispatch task to delete each CollectionVersion
           and the Collection
        """
        collection = self.get_object()

        # dependency check
        dependents = get_collection_dependents(collection)
        if dependents:
            return Response(
                {
                    "detail": _(
                        "Collection {namespace}.{name} could not be deleted "
                        "because there are other collections that require it."
                    ).format(
                        namespace=collection.namespace,
                        name=collection.name,
                    ),
                    "dependent_collection_versions": [
                        f"{dep.namespace}.{dep.name} {dep.version}" for dep in dependents
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        repositories = set()
        for version in collection.versions.all():
            for repo in version.repositories.all():
                repositories.add(repo)

        async_result = dispatch(
            delete_collection,
            exclusive_resources=list(repositories),
            kwargs={"collection_pk": collection.pk},
        )

        return OperationPostponedResponse(async_result, request)


class UnpaginatedCollectionVersionViewSet(
    api_base.LocalSettingsMixin,
    ViewNamespaceSerializerContextMixin,
    pulp_ansible_views.UnpaginatedCollectionVersionViewSet,
):
    pagination_class = None
    serializer_class = UnpaginatedCollectionVersionSerializer
    permission_classes = [access_policy.CollectionAccessPolicy]


def get_dependents(parent):
    """Given a parent collection version, return a list of
    collection versions that depend on it.
    """
    key = f"{parent.namespace}.{parent.name}"
    dependents = []
    for child in CollectionVersion.objects.filter(dependencies__has_key=key):
        spec = SimpleSpec(child.dependencies[key])
        if spec.match(Version(parent.version)):
            dependents.append(child)
    return dependents


class CollectionVersionViewSet(api_base.LocalSettingsMixin,
                               ViewNamespaceSerializerContextMixin,
                               pulp_ansible_views.CollectionVersionViewSet):
    serializer_class = CollectionVersionSerializer
    permission_classes = [access_policy.CollectionAccessPolicy]
    list_serializer_class = CollectionVersionListSerializer

    @extend_schema(
        description="Trigger an asynchronous delete task",
        responses={status.HTTP_202_ACCEPTED: AsyncOperationResponseSerializer},
    )
    def destroy(self, request: Request, *args, **kwargs) -> Response:
        """
        Allow a CollectionVersion to be deleted.
        1. Perform Dependency Check to verify that the collection version can be deleted
        2. If the collection version can’t be deleted, return the reason why
        3. If it can, dispatch task to delete CollectionVersion and clean up repository.
           If the version being deleted is the last collection version in the collection,
           remove the collection object as well.
        """
        collection_version = self.get_object()

        # dependency check
        dependents = get_dependents(collection_version)
        if dependents:
            return Response(
                {
                    "detail": _(
                        "Collection version {namespace}.{name} {version} could not be "
                        "deleted because there are other collections that require it."
                    ).format(
                        namespace=collection_version.namespace,
                        name=collection_version.collection.name,
                        version=collection_version.version,
                    ),
                    "dependent_collection_versions": [
                        f"{dep.namespace}.{dep.name} {dep.version}" for dep in dependents
                    ],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        async_result = dispatch(
            delete_collection_version,
            exclusive_resources=collection_version.repositories.all(),
            kwargs={"collection_version_pk": collection_version.pk},
        )

        return OperationPostponedResponse(async_result, request)


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
        import_obj_url = reverse("galaxy:api:content:v3:collection-import",
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

        distro_base_path = self.kwargs['path']
        filename = self.kwargs['filename']
        prefix = settings.CONTENT_PATH_PREFIX.strip('/')
        distribution = self._get_ansible_distribution(self.kwargs['path'])

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


class CollectionSignViewSet(api_base.ViewSet):
    permission_classes = [access_policy.CollectionAccessPolicy]

    def sign(self, request, *args, **kwargs):
        """Creates a signature for the content units specified in the request.

        The request body should contain a JSON object with the following keys:

        Required
            - signing_service: The name of the signing service to use
            - repository: The name of the repository to add the signatures

        Optional
            - content_units: A list of content units UUIDS to be signed.
            (if content_units is ["*"], all units under the repo will be signed)
            OR
            - namespace: Namespace name
            (if only namespace is specified, all collections under that namespace will be signed)

        Optional (one or more)
            - collection: Collection name
            (if collection name is added, all versions under that collection will be signed)
            - version: The version of the collection to sign
            (if version is specified, only that version will be signed)
        """

        signing_service = self._get_signing_service(request)
        repository = self._get_repository(request)
        content_units = self._get_content_units_to_sign(request, repository)

        sign_task = call_sign_task(signing_service, repository, content_units)
        return Response(data={"task_id": sign_task.pk}, status=status.HTTP_202_ACCEPTED)

    def _get_content_units_to_sign(self, request, repository):
        """Returns a list of pks for content units to sign.

        If `content_units` is specified in the request, it will be used.
        Otherwise, will use the filtering options specified in the request.
        namespace, collection, version can be used to filter the content units.
        """
        if request.data.get('content_units'):
            return request.data['content_units']
        else:
            try:
                namespace = request.data['namespace']
            except KeyError:
                raise ValidationError(
                    _('Missing required field: namespace')
                )

            query_params = {
                "pulp_type": "ansible.collection_version",
                "ansible_collectionversion__namespace": namespace,
            }

            if request.data.get('collection'):
                query_params['ansible_collectionversion__name'] = request.data['collection']
            if request.data.get('version'):
                query_params['ansible_collectionversion__version'] = request.data['version']

            content_units = repository.content.filter(**query_params).values_list('pk', flat=True)
            if not content_units:
                raise ValidationError(
                    _('No content units found for: %s') % query_params
                )

            return [str(item) for item in content_units]

    def _get_repository(self, request):
        """Retrieves the repository object from the request.

        :param request: the request object
        :return: the repository object
        """
        try:
            return AnsibleDistribution.objects.get(base_path=request.data["repository"]).repository
        except KeyError:
            raise ValidationError(_("repository field is required."))
        except ObjectDoesNotExist:
            raise ValidationError(_("Repository %s does not exist.") % request.data["repository"])

    def _get_signing_service(self, request):
        try:
            return SigningService.objects.get(name=request.data['signing_service'])
        except KeyError:
            raise ValidationError(_('signing_service field is required.'))
        except ObjectDoesNotExist:
            raise ValidationError(
                _('Signing service "%s" does not exist.') % request.data['signing_service']
            )


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
            move_task = call_move_content_task(**move_task_params)

        response_data['copy_task_id'] = response_data['remove_task_id'] = move_task.pk

        if settings.GALAXY_DEPLOYMENT_MODE == DeploymentMode.INSIGHTS.value:
            golden_repo = AnsibleDistribution.objects.get(
                base_path=settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH
            ).repository

            if dest_repo == golden_repo or src_repo == golden_repo:
                curate_task = dispatch(
                    curate_all_synclist_repository,
                    shared_resources=[golden_repo],
                    args=(golden_repo.name,),
                    kwargs={},
                )
                response_data['curate_all_synclist_repository_task_id'] = curate_task.pk

        return Response(data=response_data, status='202')
