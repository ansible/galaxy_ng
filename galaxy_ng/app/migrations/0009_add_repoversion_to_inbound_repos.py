from django.db import migrations


def fix_inbound_repos(apps, schema_editor):
    """Add missing init RepositoryVersion to inbound repos
    created in 0003_inbound_repo_per_namespace."""

    AnsibleRepository = apps.get_model('ansible', 'AnsibleRepository')
    RepositoryVersion = apps.get_model('core', 'RepositoryVersion')
    db_alias = schema_editor.connection.alias

    repos_missing_init_version = AnsibleRepository.objects.using(db_alias).filter(
        name__startswith='inbound-',
        next_version=0,
    )

    for repo in repos_missing_init_version:
        RepositoryVersion.objects.using(db_alias).create(
            repository=repo, number=0, complete=True)
        repo.next_version = 1
        repo.save()


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0008_rename_default_repo'),
    ]

    operations = [
        migrations.RunPython(fix_inbound_repos, elidable=True),
    ]
