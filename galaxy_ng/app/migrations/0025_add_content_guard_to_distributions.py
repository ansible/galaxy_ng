from django.db import migrations


def add_content_guard(apps, schema_editor):
    """
    Enforce that all distributions have a content guard applied
    """
    AnsibleDistribution = apps.get_model('ansible', 'AnsibleDistribution')
    ContentRedirectContentGuard = apps.get_model('galaxy', 'ContentRedirectContentGuard')

    content_guard, _ = ContentRedirectContentGuard.objects.get_or_create(
        name='ContentRedirectContentGuard',
        pulp_type='ansible.ansible'
    )

    AnsibleDistribution.objects.filter(
        content_guard=None,
        pulp_type='ansible.ansible'
    ).update(
        content_guard=content_guard
    )


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0024_contentredirectcontentguard'),
    ]

    operations = [
        migrations.RunPython(
            code=add_content_guard,
            reverse_code=migrations.RunPython.noop
        )
    ]