from pulpcore.plugin.tasking import enqueue_with_reservation
from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution, CollectionVersion


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


def dispatch_tasks_to_org_repos(collection_version_pk, action):
    """Starts tasks to add/remove CollectionVersion to/from org repos.
    Method to start tasks, not a task itself."""

    # get all org distros
    # TODO: replace with correct convention, regex in constants?
    org_distros = AnsibleDistribution.objects.filter(name__startswith='org-')

    # filter out distros which point to golden repo
    golden = AnsibleRepository.objects.get(name='automation-hub')  # use constant or param
    org_repos = set([d.repository for d in org_distros])
    try:
        org_repos.remove(golden)
    except KeyError:
        pass

    if action == 'remove':
        for repo in org_repos:
            locks = [repo]
            task_args = (collection_version_pk, repo.pk)
            enqueue_with_reservation(remove_content_from_repository, locks, args=task_args)
    elif action == 'add':
        # filter out repos with this Collection in their denylist
        # TODO ^

        # dispatch copy tasks
        for repo in org_repos:
            locks = [repo]
            task_args = (collection_version_pk, repo.pk)
            enqueue_with_reservation(add_content_to_repository, locks, args=task_args)
