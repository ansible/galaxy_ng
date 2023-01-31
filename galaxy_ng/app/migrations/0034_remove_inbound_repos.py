from django.db import migrations


def remove_inbound_repos(apps, schema_editor):
    """Remove inbound repositories and point distribution to staging repository"""

    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')
    AnsibleRepository = apps.get_model('ansible', 'AnsibleRepository')
    RepositoryContent = apps.get_model('core', 'RepositoryContent')

    repos = AnsibleRepository.objects.filter(name__startswith="inbound-")

    staging_repo = AnsibleRepository.objects.get(name="staging")

    AnsibleDistribution.objects.filter(name__startswith="inbound-").update(
        repository_id=staging_repo.pk
    )

    # is "inbound-{namespace}" RepositoryContent always empty?
    for repo in repos:
        RepositoryContent.objects.filter(repository=repo.pk).update(repository=staging_repo)

    repos.delete()

class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0033_update_validated_repo'),
    ]

    operations = [
        migrations.RunPython(
            code=remove_inbound_repos,
            reverse_code=migrations.RunPython.noop
        )
    ]
