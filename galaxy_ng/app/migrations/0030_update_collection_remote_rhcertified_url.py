from django.db import migrations

def update_collection_remote_rhcertified_url(apps, schema_editor):
    """
    Updates the existing collection remote `rh-certified` url field  
    if startswith `https://cloud.redhat.com/`.
    """
    
    CollectionRemote = apps.get_model('ansible', 'CollectionRemote')
    
    rh_remote = CollectionRemote.objects.filter(
        name='rh-certified',
        url__startswith='https://cloud.redhat.com/')

    if rh_remote:
        rh_remote.update(url='https://console.redhat.com/api/automation-hub/')


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0028_update_synclist_model'),
    ]

    operations = [
        migrations.RunPython(
            code=update_collection_remote_rhcertified_url,
            reverse_code=migrations.RunPython.noop
        )
    ]
