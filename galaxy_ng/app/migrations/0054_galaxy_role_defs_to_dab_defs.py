import logging
import time

from django.db import migrations

from galaxy_ng.app.migrations._dab_rbac import (
    create_permissions_as_operation,
    split_pulp_roles,
    copy_roles_to_role_definitions,
    migrate_role_assignments
)

logger = logging.getLogger(__name__)


def reverse_create_permissions_as_operation(apps, schema_editor):
    Permission = apps.get_model('dab_rbac', 'DABPermission')
    for perm in Permission.objects.all():
        print(f'DELETE {perm} {perm.codename}')
        perm.delete()


def reverse_copy_roles_to_role_definitions(apps, schema_editor):
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')
    for roledef in RoleDefinition.objects.all():
        print(f'DELETE {roledef} {roledef.name}')
        roledef.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0117_task_unblocked_at'),
        ('ansible', '0055_alter_collectionversion_version_alter_role_version'),
        ('galaxy', '0053_wait_for_dab_rbac'),
        ('dab_rbac', '__first__'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="team",
            options={
                "ordering": ("organization__name", "name"),
                "permissions": [("member_team", "Has all permissions granted to this team")],
            },
        ),
        migrations.AlterModelOptions(
            name="organization",
            options={
                "permissions": [("member_organization", "User is a member of this organization")]
            },
        ),
        migrations.RunPython(
            create_permissions_as_operation,
            reverse_create_permissions_as_operation
        ),
        migrations.RunPython(split_pulp_roles, migrations.RunPython.noop),
        migrations.RunPython(
            copy_roles_to_role_definitions,
            reverse_copy_roles_to_role_definitions
        ),
        migrations.RunPython(migrate_role_assignments, migrations.RunPython.noop)
    ]
