import django.core.validators
from django.db import migrations
import hashlib
import json

from django.db import migrations, models
import django.db.models.deletion

def calculate_metadata_sha256(metadata):
    """Calculates the metadata_sha256 from the other metadata fields."""
    metadata_json = json.dumps(metadata, sort_keys=True).encode("utf-8")
    hasher = hashlib.sha256(metadata_json)
    
    return hasher.hexdigest()


def add_pulp_namespace_roles(apps, schema_editor):
    """Create missing pulp ansible namespaces and add permissions."""

    AnsibleNamespace = apps.get_model('ansible', 'AnsibleNamespace')
    Namespace = apps.get_model('galaxy', 'Namespace')

    ContentType = apps.get_model("contenttypes", "ContentType")
    GroupRole = apps.get_model("core", "GroupRole")
    old_ns_type = ContentType.objects.get(app_label="galaxy", model="namespace")
    new_ns_type = ContentType.objects.get(app_label="ansible", model="ansiblenamespace")


    for old_ns in Namespace.objects.all():
        new_ns, created = AnsibleNamespace.objects.get_or_create(name=old_ns.name)

        # we'll have to handle permissions separately when we move over to the pulp ansible
        # namespaces
        roles = GroupRole.objects.filter(object_id=old_ns.pk, content_type=old_ns_type)

        # Migrate permissions
        group_roles = [
            GroupRole(
                group=r.group,
                role=r.role,
                content_type=new_ns_type,
                object_id=new_ns.pk
            ) for r in roles]
        
        GroupRole.objects.bulk_create(group_roles)




def migrate_roles(apps, schema_editor):
    # update roles with the galaxy namespace perms to have ansible namespace perms
    pass



class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0038_namespace_sync'),
    ]

    operations = [
        migrations.RunPython(
            code=add_pulp_namespace_roles,
            reverse_code=migrations.RunPython.noop
        ),
    ]
