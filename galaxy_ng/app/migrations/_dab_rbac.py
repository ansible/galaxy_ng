import logging

from django.apps import apps as global_apps

from ansible_base.rbac.management import create_dab_permissions
from ansible_base.rbac.migrations._utils import give_permissions

logger = logging.getLogger(__name__)


def create_permissions_as_operation(apps, schema_editor):
    # TODO: possibly create permissions for more apps here
    for app_label in {'ansible', 'container', 'core', 'galaxy'}:
        create_dab_permissions(global_apps.get_app_config(app_label), apps=apps)

    print(f'FINISHED CREATING PERMISSIONS')


def split_pulp_roles(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    UserRole = apps.get_model('core', 'UserRole')
    GroupRole = apps.get_model('core', 'GroupRole')

    for corerole in Role.objects.all():
        split_roles = {}
        for assignment_cls in (UserRole, GroupRole):
            for pulp_assignment in assignment_cls.objects.filter(role=corerole, content_type__isnull=False):
                if pulp_assignment.content_type_id not in split_roles:
                    new_data = {
                        'description': corerole.description,
                        'name': f'{corerole.name}_{pulp_assignment.content_type.model}'
                    }
                    new_role = Role(**new_data)
                    new_role.save()
                    split_roles[pulp_assignment.content_type_id] = new_role
            pulp_assignment.role = split_roles[pulp_assignment.content_type_id]
            pulp_assignment.save(update_fields=['role'])


def copy_roles_to_role_definitions(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    DABPermission = apps.get_model('dab_rbac', 'DABPermission')
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')

    for corerole in Role.objects.all():
        dab_perms = []
        for perm in corerole.permissions.prefetch_related('content_type').all():
            dabperm = DABPermission.objects.filter(
                codename=perm.codename,
                content_type=perm.content_type
            ).first()
            if dabperm:
                dab_perms.append(dabperm)

        if dab_perms:
            roledef, created = RoleDefinition.objects.get_or_create(name=corerole.name)
            if created:
                print(f'CREATED RoleDefinition from {corerole} {corerole.name}')
                roledef.permissions.set(dab_perms)


def migrate_role_assignments(apps, schema_editor):
    UserRole = apps.get_model('core', 'UserRole')
    GroupRole = apps.get_model('core', 'GroupRole')
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')
    RoleUserAssignment = apps.get_model('dab_rbac', 'RoleUserAssignment')
    RoleTeamAssignment = apps.get_model('dab_rbac', 'RoleTeamAssignment')

    for user_role in UserRole.objects.all():
        rd = RoleDefinition.objects.filter(name=user_role.role.name).first()
        if not rd:
            continue
        if not user_role.object_id:
            # system role
            RoleUserAssignment.objects.create(role_definition=rd, user=user_role.user)
        else:
            give_permissions(apps, rd, users=[user_role.user], object_id=user_role.object_id, content_type_id=user_role.content_type_id)

    for group_role in GroupRole.objects.all():
        rd = RoleDefinition.objects.filter(name=group_role.role.name).first()
        if not rd:
            continue
        actor = group_role.group.team
        if not group_role.object_id:
            RoleTeamAssignment.objects.create(role_definition=rd, team=actor)
        else:
            give_permissions(apps, rd, teams=[actor], object_id=group_role.object_id, content_type_id=group_role.content_type_id)
