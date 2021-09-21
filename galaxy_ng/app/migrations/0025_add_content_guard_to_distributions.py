from django.db import migrations

def add_content_guard(apps, schema_editor):
    """
    Enforce that all distributions have a content guard applied
    """
    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')
    ContentGuard = apps.get_model('galaxy', 'CollectionDownloadContentGuard')

    AnsibleDistribution.objects.filter(
        content_guard=None,
        pulp_type='ansible.ansible'
    ).update(
        content_guard=ContentGuard.objects.get_or_create(
            pulp_type='ansible.ansible'
        )[0]
    )


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0024_collectiondownloadcontentguard'),
    ]

    operations = [
        migrations.RunPython(
            code=add_content_guard,
            reverse_code=migrations.RunPython.noop
        )
    ]
