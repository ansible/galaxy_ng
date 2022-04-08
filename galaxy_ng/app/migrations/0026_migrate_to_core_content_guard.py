from django.db import migrations


def replace_content_guard(apps, schema_editor):
    """
    Enforce that all distributions have a content guard applied
    """
    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')
    ContentRedirectContentGuard = apps.get_model('core', 'ContentRedirectContentGuard')

    OldContentGuard = apps.get_model('core', 'ContentGuard')

    # Delete the old content guard manually since it doesn't seem to get garbage collected
    # by deleting the content guard.
    OldContentGuard.objects.filter(name='ContentRedirectContentGuard').delete()

    content_guard, _ = ContentRedirectContentGuard.objects.get_or_create(
        name='ContentRedirectContentGuard',
        pulp_type='core.content_redirect'
    )

    AnsibleDistribution.objects.filter(pulp_type='ansible.ansible').update(
        content_guard=content_guard
    )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0087_taskschedule'),
        ('galaxy', '0025_add_content_guard_to_distributions'),
    ]

    operations = [
        migrations.RunPython(
            code=replace_content_guard,
            reverse_code=migrations.RunPython.noop
        ),
    ]
