from pulp_ansible.app.models import (
    CollectionVersion,
    AnsibleRepository,
    AnsibleDistribution
)


def create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(
        name=name, base_path=name, repository=repo
    )
    return repo


def get_create_version_in_repo(namespace, collection, repo, **kwargs):
    collection_version, _ = CollectionVersion.objects.get_or_create(
        namespace=namespace,
        name=collection.name,
        collection=collection,
        **kwargs,
    )
    qs = CollectionVersion.objects.filter(pk=collection_version.pk)
    with repo.new_version() as new_version:
        new_version.add_content(qs)
    return collection_version
