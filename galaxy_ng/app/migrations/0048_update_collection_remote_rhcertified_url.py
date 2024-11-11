from django.db import migrations

def update_collection_remote_rhcertified_url(apps, schema_editor):
    """
    Updates the existing collection remote `rh-certified` url field
    to add `content/published/`.
    """

    CollectionRemote = apps.get_model('ansible', 'CollectionRemote')

    rh_remote = CollectionRemote.objects.filter(name='rh-certified').first()

    if rh_remote and rh_remote.url == 'https://console.redhat.com/api/automation-hub/':
        rh_remote.url = rh_remote.url.replace('https://console.redhat.com/api/automation-hub/', 'https://console.redhat.com/api/automation-hub/content/published/')
        rh_remote.save()


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0047_update_role_search_vector_trigger'),
    ]

    operations = [
        migrations.RunPython(
            code=update_collection_remote_rhcertified_url,
            reverse_code=migrations.RunPython.noop
        )
    ]
