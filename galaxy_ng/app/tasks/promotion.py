from pulp_ansible.app.models import AnsibleRepository, CollectionVersion


def add_content_to_repository(collection_version_pk, repository_pk):
    """
    Add a CollectionVersion to repository.
    Args:
        collection_version_pk: The pk of the CollectionVersion to add to repository.
        repository_pk: The pk of the AnsibleRepository to add the CollectionVersion to.
    """
    repository = AnsibleRepository.objects.get(pk=repository_pk)
    qs = CollectionVersion.objects.filter(pk=collection_version_pk)
    with repository.new_version() as new_version:
        new_version.add_content(qs)


def remove_content_from_repository(collection_version_pk, repository_pk):
    """
    Remove a CollectionVersion from a repository.
    Args:
        collection_version_pk: The pk of the CollectionVersion to remove from repository.
        repository_pk: The pk of the AnsibleRepository to remove the CollectionVersion from.
    """
    repository = AnsibleRepository.objects.get(pk=repository_pk)
    qs = CollectionVersion.objects.filter(pk=collection_version_pk)
    with repository.new_version() as new_version:
        new_version.remove_content(qs)
