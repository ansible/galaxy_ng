from django.db import migrations

def update_collection_remote_rhcertified_url(apps, schema_editor):
    """
    Updates the existing collection remote `rh-certified` url field  
    if startswith `https://cloud.redhat.com/`.
    """
    
    CollectionRemote = apps.get_model('ansible', 'CollectionRemote')
    
    rh_remote = CollectionRemote.objects.filter(name='rh-certified').first()

    if rh_remote and rh_remote.url.startswith('https://cloud.redhat.com/'):
        rh_remote.url = rh_remote.url.replace('https://cloud.redhat.com/', 'https://console.redhat.com/')
        rh_remote.save()


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0029_move_perms_to_roles'),
    ]

    operations = [
        migrations.RunPython(
            code=update_collection_remote_rhcertified_url,
            reverse_code=migrations.RunPython.noop
        )
    ]
