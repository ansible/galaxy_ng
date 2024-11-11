from django.db import migrations


def set_collection_remote_type(apps, schema_editor):

    CollectionRemote = apps.get_model('ansible', 'CollectionRemote')
    for cremote in CollectionRemote.objects.all():
        if cremote.pulp_type != 'ansible.collection':
            cremote.pulp_type = 'ansible.collection'
            cremote.save()


class Migration(migrations.Migration):

    dependencies = [
        ("galaxy", "0039_legacyroledownloadcount"),
    ]

    operations = [
        migrations.RunPython(
            code=set_collection_remote_type,
            reverse_code=migrations.RunPython.noop
        ),
    ]
