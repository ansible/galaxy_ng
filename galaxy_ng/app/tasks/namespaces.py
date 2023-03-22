from pulp_ansible.app.models import AnsibleNamespaceMetadata, AnsibleNamespace
from pulpcore.plugin.tasking import add_and_remove, dispatch
from pulpcore.plugin.models import RepositoryContent


def dispatch_create_pulp_namespace_metadata(galaxy_ns):
    # get metadata values
    links = {x.name: x.url for x in galaxy_ns.links.all()}

    namespace_data = {
        "company": galaxy_ns.company,
        "email": galaxy_ns.email,
        "description": galaxy_ns.description,
        "resources": galaxy_ns.resources,
        "links": links,
        "avatar_sha256": None,
        "avatar_url": galaxy_ns.avatar_url,
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
        galaxy_ns.save

    else:
        metadata.save()
        galaxy_ns.last_created_pulp_metadata = metadata
        galaxy_ns.save

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
            add_content_units=[namespace_pk, ],
            remove_content_units=[]
        )
