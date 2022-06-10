from django.db import migrations


# This migration used to assign a bunch of permissions to the system:partner-engineer group
# back when galaxy_ng was only deployed on console.redhat.com. Since this was a data migration
# that was only used for console.redhat.com, it can be safely removed.
class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0012_move_collections_by_certification'),
    ]

    operations = [
        migrations.RunPython(
            code=migrations.RunPython.noop,
        ),
    ]
