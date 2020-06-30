from django.db import migrations

def create_inbound_repo_per_namespace(apps, schema_editor):
    AnsibleRepository = apps.get_model('ansible', 'AnsibleRepository')
    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')
    Namespace = apps.get_model('galaxy', 'Namespace')
    db_alias = schema_editor.connection.alias

    for namespace in Namespace.objects.using(db_alias).all():
        name = f'inbound-{namespace.name}'
        repo = AnsibleRepository.objects.using(db_alias).create(
            name=name,
            pulp_type='ansible.ansible',
        )
        distro = AnsibleDistribution.objects.using(db_alias).create(
            name=name,
            base_path=name,
            repository=repo,
            pulp_type='ansible.ansible',
        )


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0002_add_synclist_20200330_squashed'),
    ]

    operations = [
        migrations.RunPython(create_inbound_repo_per_namespace, elidable=True)
    ]
