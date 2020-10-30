from django.db import migrations
from django.core import exceptions


# note: using assign_perm from guardian.shortcuts doesn't work in migrations
# https://github.com/django-guardian/django-guardian/issues/281#issuecomment-156264129
# The following function is adapted from https://gist.github.com/xuhcc/67871719116bdc0fee6c
def assign_perm(apps, perm, owner):
    PermissionModel = apps.get_model('auth', 'Permission')
    app_label, codename = perm.split('.', 1)

    perm = PermissionModel.objects.get(
        content_type__app_label=app_label,
        codename=codename)

    owner.permissions.add(perm)


def convert_namespace_groups_to_permissions(apps, schema_editor):
    GroupModel = apps.get_model('galaxy', 'Group')
    pe_perms = [
        # groups
        'galaxy.view_group',
        'galaxy.delete_group',
        'galaxy.add_group',
        'galaxy.change_group',

        # users
        'galaxy.view_user',
        'galaxy.delete_user',
        'galaxy.add_user',
        'galaxy.change_user',

        # collections
        'ansible.modify_ansible_repo_content',

        # namespaces
        'galaxy.add_namespace',
        'galaxy.change_namespace',
        'galaxy.upload_to_namespace',
    ]

    try:
        pe_group = GroupModel.objects.get(name="system:partner-engineers")
        for perm in pe_perms:
            assign_perm(apps, perm, pe_group)
    except exceptions.ObjectDoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0012_move_collections_by_certification'),
    ]

    operations = [
        migrations.RunPython(
            code=convert_namespace_groups_to_permissions,
        ),
    ]
