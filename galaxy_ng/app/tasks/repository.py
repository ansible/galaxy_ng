def update_ansible_repository(repository_pk, data, partial=False):
    """Apply a Galaxy UI repository edit with Pulp's normal save path.

    Reloads the repository after exclusive reservation so concurrent version
    counters are not overwritten, then uses AnsibleRepositoryDetailSerializer
    so last_synced_metadata_time reset and retain_repo_versions cleanup run.
    """
    from galaxy_ng.app.api.v3.serializers.sync import AnsibleRepositoryDetailSerializer
    from pulp_ansible.app.models import AnsibleRepository

    instance = AnsibleRepository.objects.get(pk=repository_pk)
    serializer = AnsibleRepositoryDetailSerializer(
        instance,
        data=data,
        partial=partial,
        context={"request": None},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
