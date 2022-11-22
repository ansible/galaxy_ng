from django.db import migrations


def update_validated_repo(apps, schema_editor):
    """Add a content_guard to the distribution of the validated repo"""

    ContentRedirectContentGuard = apps.get_model('core', 'ContentRedirectContentGuard')
    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')

    content_guard = ContentRedirectContentGuard.objects.get(
        name='ContentRedirectContentGuard',
        pulp_type='core.content_redirect'
    )

    AnsibleDistribution.objects.filter(name="validated").update(
        content_guard=content_guard
    )

class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0032_add_validated_repo'),
    ]

    operations = [
        migrations.RunPython(
            code=update_validated_repo,
            reverse_code=migrations.RunPython.noop
        )
    ]
