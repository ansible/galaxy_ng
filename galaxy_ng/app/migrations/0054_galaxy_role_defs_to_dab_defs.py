import logging
import time

from django.db import migrations

from django.apps import apps as global_apps

from ansible_base.rbac.management import create_dab_permissions

logger = logging.getLogger(__name__)


def create_permissions_as_operation(apps, schema_editor):
    create_dab_permissions(global_apps.get_app_config("galaxy"), apps=apps)
    Permission = apps.get_model('auth', 'Permission')
    DABPermission = apps.get_model('dab_rbac', 'DABPermission')
    for perm in Permission.objects.all():
        print(f'CREATE {perm} {perm.codename}')
        dab_perm, created = DABPermission.objects.get_or_create(
            codename=perm.codename,
            content_type=perm.content_type,
            name=perm.name
        )

    print(f'FINISHED CREATING PERMISSIONS')


def reverse_create_permissions_as_operation(apps, schema_editor):
    Permission = apps.get_model('dab_rbac', 'DABPermission')
    for perm in Permission.objects.all():
        print(f'DELETE {perm} {perm.codename}')
        perm.delete()


def copy_roles_to_role_definitions(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    DABPermission = apps.get_model('dab_rbac', 'DABPermission')
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')

    for corerole in Role.objects.all():
        print(f'CREATE {corerole} {corerole.name}')
        roledef, _ = RoleDefinition.objects.get_or_create(name=corerole.name)

        content_types = set()
        for perm in corerole.permissions.all():
            dabperm = DABPermission.objects.get(
                codename=perm.codename,
                content_type=perm.content_type,
                name=perm.name
            )
            roledef.permissions.add(dabperm)
            content_types.add(perm.content_type)

        # FIXME - when dab supports multi-content type roles
        content_types = list(content_types)
        if len(content_types) == 1:
            roledef.content_type = content_types[0]
            roledef.content_type_id = content_types[0].id
            roledef.save()


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
        # migrations.RunPython(
        #     copy_roles_to_role_definitions,
        #     reverse_copy_roles_to_role_definitions
        # ),
    ]
