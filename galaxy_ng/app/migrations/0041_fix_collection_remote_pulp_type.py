import django.core.validators
from django.db import migrations
import hashlib
import json

from django.db import migrations, models
import django.db.models.deletion


def set_collection_remote_type(apps, schema_editor):

    CollectionRemote = apps.get_model('ansible', 'CollectionRemote')
    for cremote in CollectionRemote.objects.all():
        if cremote.pulp_type != 'ansible.collection':
            cremote.pulp_type = 'ansible.collection'
            cremote.save()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0106_alter_artifactdistribution_distribution_ptr_and_more"),
        ("galaxy", "0040_alter_containerregistryremote_remote_ptr"),
    ]

    operations = [
        migrations.RunPython(
            code=set_collection_remote_type,
            reverse_code=migrations.RunPython.noop
        ),
    ]
