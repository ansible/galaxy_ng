import json
import logging
from urllib.parse import quote, urlencode

from django.core import exceptions
from django.utils.translation import gettext_lazy as _
from django.http.request import HttpRequest

from pulpcore.plugin.tasking import dispatch

from pulp_container.app import models as container_models

from galaxy_ng.app.api.ui import serializers
from galaxy_ng.app import models


log = logging.getLogger(__name__)


CATALOG_API = "https://catalog.redhat.com/api/containers/v1/repositories"


class CouldNotCreateContainerError(Exception):
    def __init__(self, remote_name, error=""):
        self.message = _(
            "Failed to create container {remote_name}. {error}".format(
                remote_name=remote_name, error=error)
        )

        super().__init__(self.message)


def _get_request(request_data):
    request = HttpRequest()

    for k, v in request_data.items():
        setattr(request, k, v)

    return request


def _parse_catalog_repositories(response_data):
    containers = []

    for container in response_data['data']:
        containers.append({
            "name": container['repository'],
            "upstream_name": container['repository'],
            "description": container['display_data']['short_description'],
            "readme": container['display_data']['long_description_markdown'],
        })

    return containers


def _update_distro_readme_and_description(distro, container_data):
    readme = models.ContainerDistroReadme.objects.get_or_create(container=distro)[0]
    readme.text = container_data['readme']
    readme.save()

    distro.description = container_data['description']
    distro.save()


def create_or_update_remote_container(container_data, registry_pk, request_data):
    # check if a distro matching the base name exists
    remote_repo_type = container_models.ContainerRepository.get_pulp_type()

    try:
        distro = container_models.ContainerDistribution.objects.get(
            base_path=container_data['name'])

        repo = distro.repository

        # If a distro matching the container name exists, and it's a remote repository and
        # it has a container remote attached to it that's associated with the selected
        # registry, update the container's readme and description.
        if repo.pulp_type == remote_repo_type and repo.remote is not None:
            try:
                remote_registry = models.ContainerRegistryRepos.objects.get(
                    repository_remote=repo.remote).registry
                if remote_registry and remote_registry.pk == registry_pk:
                    _update_distro_readme_and_description(distro, container_data)
                    return

            except exceptions.ObjectDoesNotExist:
                raise CouldNotCreateContainerError(
                    container_data['name'],
                    error=_(
                        "A remote container with this name already exists, "
                        "but is not associated with any registry.")
                )

        else:
            raise CouldNotCreateContainerError(
                container_data['name'],
                error=_("A local container with this name already exists.")
            )

    except exceptions.ObjectDoesNotExist:
        # If no distributions match the selected container, create one.
        request = _get_request(request_data)
        serializer = serializers.ContainerRemoteSerializer(
            data={
                "name": container_data['name'],
                "upstream_name": container_data['name'],
                "registry": str(registry_pk)
            }, context={"request": request}
        )

        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            CouldNotCreateContainerError(
                container_data['name'],
                error=str(e)
            )
        serializer.create(serializer.validated_data)

        distro = container_models.ContainerDistribution.objects.get(
            base_path=container_data['name'])

        _update_distro_readme_and_description(distro, container_data)


def index_execution_environments_from_redhat_registry(registry_pk, request_data):
    registry = models.ContainerRegistryRemote.objects.get(pk=registry_pk)
    remotes = []

    query = {
        "filter": "build_categories=in=('Automation execution environment')",
        "page": 0,
        "sort_by": "creation_date[asc]"
    }

    # Iterate through the pages on the API response and add the relevant information
    # about each container repository.
    while True:
        url = CATALOG_API + "?" + urlencode(query, quote_via=quote)
        downloader = registry.get_downloader(url=url)
        download_result = downloader.fetch()
        with open(download_result.path) as fd:
            data = json.load(fd)
            remotes = remotes + _parse_catalog_repositories(data)
            if len(data['data']) == data['page_size']:
                query['page'] += 1
            else:
                break

    for remote in remotes:
        # create a subtask for each remote, so that if one fails, we can throw a usable error
        # message for the user to look at and prevent the rest of the repositories from failing.
        dispatch(
            create_or_update_remote_container,
            kwargs={
                "container_data": remote,
                "registry_pk": registry.pk,
                "request_data": request_data
            },
            exclusive_resources=["/api/v3/distributions/"]
        )
