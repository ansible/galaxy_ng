import aiohttp
import asyncio
import contextlib
import xml.etree.ElementTree as ET

from django.db import transaction
from django.forms.fields import ImageField
from django.core.exceptions import ValidationError
from pulpcore.plugin.files import PulpTemporaryUploadedFile

from pulpcore.plugin.download import HttpDownloader

from pulp_ansible.app.models import AnsibleNamespaceMetadata, AnsibleNamespace
from pulpcore.plugin.tasking import add_and_remove, dispatch
from pulpcore.plugin.models import RepositoryContent, Artifact, ContentArtifact

from galaxy_ng.app.models import Namespace


MAX_AVATAR_SIZE = 3 * 1024 * 1024  # 3MB


def dispatch_create_pulp_namespace_metadata(galaxy_ns, download_logo):

    dispatch(
        _create_pulp_namespace,
        kwargs={
            "galaxy_ns_pk": galaxy_ns.pk,
            "download_logo": download_logo,
        }
    )


def _download_avatar(url, namespace_name):
    # User-Agent needs to be added to avoid timing out on throtled servers.
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:71.0)'  # +
        ' Gecko/20100101 Firefox/71.0'
    }
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=600, sock_read=600)
    conn = aiohttp.TCPConnector(loop=asyncio.get_event_loop(), force_close=True)
    session = aiohttp.ClientSession(
        connector=conn, timeout=timeout, headers=headers, requote_redirect_url=False
    )

    try:
        downloader = HttpDownloader(url, session=session)
        img = downloader.fetch()
    except Exception:  # noqa
        # FIXME(cutwater): Handling base exception class is a bad practice, as well as ignoring it.
        return
    finally:
        # FIXME(cutwater): The `asyncio.get_event_loop()` must not be used in the code.
        #   It is deprecated and it's original behavior may change in future.
        #   Users must not rely on the original behavior.
        #   https://docs.python.org/3/library/asyncio-eventloop.html#asyncio.get_event_loop
        asyncio.get_event_loop().run_until_complete(session.close())

    # Limit size of the avatar to avoid memory issues when validating it
    if img.artifact_attributes["size"] > MAX_AVATAR_SIZE:
        raise ValidationError(
            f"Avatar for {namespace_name} on {url} larger than {MAX_AVATAR_SIZE / 1024 / 1024}MB"
        )

    with contextlib.suppress(Artifact.DoesNotExist):
        return Artifact.objects.get(sha256=img.artifact_attributes["sha256"])

    with open(img.path, "rb") as f:
        tf = PulpTemporaryUploadedFile.from_file(f)
        try:
            ImageField().to_python(tf)
        except ValidationError:
            # Not a PIL valid image lets handle SVG case
            tag = None
            with contextlib.suppress(ET.ParseError):
                f.seek(0)
                tag = ET.parse(f).find(".").tag
            if tag != '{http://www.w3.org/2000/svg}svg':
                raise ValidationError(
                    f"Provided avatar_url for {namespace_name} on {url} is not a valid image"
                )

        # the artifact has to be saved before the file is closed, or s3transfer
        # will throw an error.
        artifact = Artifact.init_and_validate(tf)
        artifact.save()

        return artifact


def _create_pulp_namespace(galaxy_ns_pk, download_logo):
    # get metadata values
    galaxy_ns = Namespace.objects.get(pk=galaxy_ns_pk)
    links = {x.name: x.url for x in galaxy_ns.links.all()}

    avatar_artifact = None

    if download_logo:
        avatar_artifact = _download_avatar(galaxy_ns._avatar_url, galaxy_ns.name)

    avatar_sha = None
    if avatar_artifact:
        avatar_sha = avatar_artifact.sha256

    namespace_data = {
        "company": galaxy_ns.company,
        "email": galaxy_ns.email,
        "description": galaxy_ns.description,
        "resources": galaxy_ns.resources,
        "links": links,
        "avatar_sha256": avatar_sha,
        "name": galaxy_ns.name,
    }

    namespace_data["name"] = galaxy_ns.name
    namespace, created = AnsibleNamespace.objects.get_or_create(name=namespace_data["name"])
    metadata = AnsibleNamespaceMetadata(namespace=namespace, **namespace_data)
    metadata.calculate_metadata_sha256()
    content = AnsibleNamespaceMetadata.objects.filter(
        metadata_sha256=metadata.metadata_sha256
    ).first()

    # If the metadata already exists, don't do anything
    if content:
        content.touch()
        galaxy_ns.last_created_pulp_metadata = content
        galaxy_ns.save()

    else:
        with transaction.atomic():
            metadata.save()
            ContentArtifact.objects.create(
                artifact=avatar_artifact,
                content=metadata,
                relative_path=f"{metadata.name}-avatar"
            )
            galaxy_ns.last_created_pulp_metadata = metadata
            galaxy_ns.save()

        # get list of local repositories that have a collection with the matching
        # namespace
        # We're not bothering to determine if the collection is in a distro or the latest
        # version of a repository because galaxy_ng retains one repo version by default
        repo_content_qs = (
            RepositoryContent.objects
            .select_related("content__ansible_collectionversion")
            .order_by("repository__pk")
            .filter(
                repository__remote=None,
                content__ansible_collectionversion__namespace=galaxy_ns.name,
                version_removed=None,
            )
            .distinct("repository__pk")
        )

        repos = [x.repository for x in repo_content_qs]

        return dispatch(
            _add_namespace_metadata_to_repos,
            kwargs={
                "namespace_pk": metadata.pk,
                "repo_list": [x.pk for x in repos],
            },
            exclusive_resources=repos
        )


def _add_namespace_metadata_to_repos(namespace_pk, repo_list):
    for pk in repo_list:
        add_and_remove(
            pk,
            add_content_units=[namespace_pk],
            remove_content_units=[]
        )
