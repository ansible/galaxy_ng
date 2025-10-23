import logging
from itertools import chain

from django.apps import apps as global_apps

from rest_framework.exceptions import ValidationError

from ansible_base.rbac.migrations._utils import give_permissions
from ansible_base.rbac.validators import LocalValidators, combine_values
from ansible_base.rbac.management._old import create_dab_permissions as old_create_dab_permissions
from ansible_base.rbac import permission_registry


logger = logging.getLogger(__name__)


PULP_TO_ROLEDEF = {
    'galaxy.auditor': 'Platform Auditor',
}


ROLEDEF_TO_PULP = {
    'Platform Auditor': 'galaxy.auditor',
}


def give_global_permission_to_actor(role_definition, actor, apps):
    """
    Migration-safe utility function to give global permission to an actor (user or team).

    This function replicates the logic from RoleDefinition.give_global_permission()
    but works with migration fake models that don't have custom methods.

    Args:
        role_definition: RoleDefinition instance (can be fake model from migration)
        actor: User or Team instance to grant permission to
        apps: Django apps registry from migration context
    """
    from django.conf import settings
    from rest_framework.exceptions import ValidationError

    if role_definition.content_type is not None:
        raise ValidationError("Role definition content type must be null to assign globally")

    # Get the assignment classes through apps registry (migration-safe)
    RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
    RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")

    if actor._meta.model_name == "user":
        if not settings.ANSIBLE_BASE_ALLOW_SINGLETON_USER_ROLES:
            raise ValidationError("Global roles are not enabled for users")
        kwargs = {"object_role": None, "user": actor, "role_definition": role_definition}
        cls = RoleUserAssignment
    elif hasattr(actor, "_meta") and actor._meta.model_name == "team":
        # In migration context, check by model name since isinstance checks might fail
        if not settings.ANSIBLE_BASE_ALLOW_SINGLETON_TEAM_ROLES:
            raise ValidationError("Global roles are not enabled for teams")
        kwargs = {"object_role": None, "team": actor, "role_definition": role_definition}
        cls = RoleTeamAssignment
    else:
        raise RuntimeError(
            f'Cannot give permission for {actor} (type: {type(actor)}, model_name: {getattr(actor._meta, "model_name", "unknown")}), must be a user or team'
        )

    assignment, _ = cls.objects.get_or_create(**kwargs)

    # Clear any cached permissions
    if actor._meta.model_name == "user":
        if hasattr(actor, "_singleton_permissions"):
            delattr(actor, "_singleton_permissions")
    else:
        # when team permissions change, users in memory may be affected by this
        # but there is no way to know what users, so we use a global flag
        from ansible_base.rbac.evaluations import bound_singleton_permissions

        bound_singleton_permissions._team_clear_signal = True

    return assignment

def pulp_role_to_single_content_type_or_none(pulprole):
    if pulprole.name.startswith('galaxy.') and pulprole.name.endswith('_global'):
        # Special case for roles which were intentionally split out with the intent to be global
        # These are created specifically to accomidate global assignments with roles that "look"
        # like they should be object-based
        return None
    content_types = {perm.content_type for perm in pulprole.permissions.all()}
    if len(content_types) == 1:
        return next(iter(content_types))
    return None


def create_permissions_as_operation(apps, schema_editor):
    # NOTE: this is a snapshot version of the DAB RBAC permission creation logic
    # normally this runs post_migrate, but this exists to keep old logic
    for app_label in {'ansible', 'container', 'core', 'galaxy'}:
        app_config = global_apps.get_app_config(app_label)
        old_create_dab_permissions(app_config, apps=apps)

    print('FINISHED CREATING PERMISSIONS')


def split_pulp_roles(apps, schema_editor):
    '''
    For every user&group role that is tied to a specific content object,
    split the role out into a new single content type role with permissions
    that are only relevant to that content object. Afterwards, swap the
    [User|Group]Role's .role with the new role.
    '''
    Role = apps.get_model('core', 'Role')
    UserRole = apps.get_model('core', 'UserRole')
    GroupRole = apps.get_model('core', 'GroupRole')

    for corerole in Role.objects.all():
        split_roles = {}

        # Compute the inferred content type of the role
        inferred_content_type = pulp_role_to_single_content_type_or_none(corerole)

        for assignment_cls in (UserRole, GroupRole):
            # Filter assignments where content_type doesn't match the inferred content type
            # This handles both cases: assignments with a different content type than inferred,
            # and global assignments (content_type=None) when the role has an inferred type
            assignments_to_split = assignment_cls.objects.filter(role=corerole)
            if inferred_content_type:
                # If the role has an inferred content type, only split assignments
                # that don't match it (excluding None/global assignments)
                assignments_to_split = assignments_to_split.exclude(content_type=inferred_content_type)
            else:
                # If the role has no inferred content type, split all object-level assignments
                assignments_to_split = assignments_to_split.filter(content_type__isnull=False)

            for pulp_assignment in assignments_to_split:
                role_suffix = pulp_assignment.content_type.model if pulp_assignment.content_type else "global"
                ct_id = pulp_assignment.content_type_id
                if ct_id not in split_roles:

                    # Get all permissions relevant to this content model.
                    # If any model (like synclist) hasn't been registered in the permission
                    # system, it should not be split/recreated ...
                    if pulp_assignment.content_type:
                        cls = apps.get_model(pulp_assignment.content_type.app_label, pulp_assignment.content_type.model)
                        try:
                            ct_codenames = combine_values(LocalValidators.permissions_allowed_for_role(cls))
                        except ValidationError:
                            continue
                    else:
                        # Global assignment
                        ct_codenames = None

                    # Make a new role for this content model
                    new_data = {
                        'description': corerole.description,
                        'name': f'{corerole.name}_{role_suffix}'
                    }
                    new_role = Role(**new_data)
                    new_role.save()

                    # Add the necesarry permissions to the new role ...
                    for perm in pulp_assignment.role.permissions.all():
                        # The pulp role may have had permissions related to some other
                        # content model we're not interested in, so we will skip adding those.
                        if ct_codenames and perm.codename not in ct_codenames:
                            continue
                        new_role.permissions.add(perm)

                    split_roles[ct_id] = new_role

                pulp_assignment.role = split_roles[ct_id]
                pulp_assignment.save(update_fields=['role'])


def model_class(apps, ct):
    "Utility method because we can not count on method being available in migrations"
    return apps.get_model(ct.app_label, ct.model)


def copy_roles_to_role_definitions(apps, schema_editor):
    Role = apps.get_model('core', 'Role')
    DABPermission = apps.get_model('dab_rbac', 'DABPermission')
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')
    try:
        DABContentType = apps.get_model('dab_rbac', 'DABContentType')
        logger.info('Running copy_roles_to_role_definitions with DAB RBAC post-remote-permission models')
    except LookupError:
        DABContentType = apps.get_model('contenttypes', 'ContentType')
        logger.info('Running copy_roles_to_role_definitions with DAB RBAC original model state')

    for corerole in Role.objects.all():
        dab_perms = []
        for perm in corerole.permissions.prefetch_related('content_type').all():
            ct = perm.content_type
            model_cls = model_class(apps, ct)
            if not permission_registry.is_registered(model_cls):
                continue
            dabct = DABContentType.objects.filter(model=ct.model, app_label=ct.app_label).first()
            if dabct is None:
                raise dabct.DoesNotExist(
                    f'Content type ({ct.app_label}, {ct.model}) for registered model {model_cls} not found as DABContentType'
                    f'\nexisting: {list(DABContentType.objects.values_list("model", flat=True))}'
                )
            dabperm = DABPermission.objects.filter(
                codename=perm.codename,
                content_type=dabct
            ).first()
            if dabperm:
                dab_perms.append(dabperm)

        if dab_perms:
            roledef_name = PULP_TO_ROLEDEF.get(corerole.name, corerole.name)
            content_type = pulp_role_to_single_content_type_or_none(corerole)
            dabct = None
            if content_type:
                dabct = DABContentType.objects.filter(model=content_type.model, app_label=content_type.app_label).first()
                if dabct is None:
                    raise dabct.DoesNotExist(
                        f'Content type ({content_type.app_label}, {content_type.model}) not found as DABContentType'
                        f'\nexisting: {list(DABContentType.objects.values_list("model", flat=True))}'
                    )
            roledef, created = RoleDefinition.objects.get_or_create(
                name=roledef_name,
                defaults={
                    'description': corerole.description or corerole.name,
                    'managed': corerole.locked,
                    'content_type': dabct,
                }
            )
            if created:
                print(f'CREATED RoleDefinition from {corerole} {corerole.name}')
                roledef.permissions.set(dab_perms)


def migrate_role_assignments(apps, schema_editor):
    UserRole = apps.get_model('core', 'UserRole')
    GroupRole = apps.get_model('core', 'GroupRole')
    Group = apps.get_model('auth', 'Group')
    Team = apps.get_model('galaxy', 'Team')
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')
    RoleUserAssignment = apps.get_model('dab_rbac', 'RoleUserAssignment')
    RoleTeamAssignment = apps.get_model('dab_rbac', 'RoleTeamAssignment')

    # Migrate user role assignments
    for user_role in UserRole.objects.all():
        rd = RoleDefinition.objects.filter(name=user_role.role.name).first()
        if not rd:
            continue

        # Validate content_type matches
        if user_role.object_id:
            # Object-level assignment: role should have matching content_type
            if rd.content_type_id != user_role.content_type_id:
                raise ValueError(
                    f"Content type mismatch for user role assignment {user_role.id}: "
                    f"role '{rd.name}' has content_type_id={rd.content_type_id}, "
                    f"but assignment has content_type_id={user_role.content_type_id}"
                )
            give_permissions(apps, rd, users=[user_role.user], object_id=user_role.object_id, content_type_id=user_role.content_type_id)
        else:
            # Global assignment: role should have no content_type
            if rd.content_type is not None:
                raise ValueError(
                    f"Content type mismatch for global user role assignment {user_role.id}: "
                    f"role '{rd.name}' has content_type={rd.content_type}, "
                    f"but assignment is global (content_type=None)"
                )
            RoleUserAssignment.objects.create(role_definition=rd, user=user_role.user)

    # Migrate team/group role assignments
    for group_role in GroupRole.objects.all():
        rd = RoleDefinition.objects.filter(name=group_role.role.name).first()
        if not rd:
            continue

        actor = Team.objects.filter(group=group_role.group).first()
        if actor is None:
            continue

        # Validate content_type matches
        if group_role.object_id:
            # Object-level assignment: role should have matching content_type
            if rd.content_type_id != group_role.content_type_id:
                raise ValueError(
                    f"Content type mismatch for team role assignment {group_role.id}: "
                    f"role '{rd.name}' has content_type_id={rd.content_type_id}, "
                    f"but assignment has content_type_id={group_role.content_type_id}"
                )
            give_permissions(apps, rd, teams=[actor], object_id=group_role.object_id, content_type_id=group_role.content_type_id)
        else:
            # Global assignment: role should have no content_type
            if rd.content_type is not None:
                raise ValueError(
                    f"Content type mismatch for global team role assignment {group_role.pk}: "
                    f"role '{rd.name}' has content_type={rd.content_type}, "
                    f"but assignment is global (content_type=None)"
                )
            RoleTeamAssignment.objects.create(role_definition=rd, team=actor)

    # Create the local member role if it does not yet exist
    from ansible_base.rbac.permission_registry import permission_registry

    # galaxy_ng/app/settings.py - ANSIBLE_BASE_MANAGED_ROLE_REGISTRY
    rd_template = permission_registry.get_managed_role_constructor('team_member')
    member_rd, created = rd_template.get_or_create(apps)
    if created:
        logger.info(f'Created role definition {member_rd.name}')

    # In DAB RBAC, team users are saved as a role assignment
    # Migrate the pulp group users (relationship) to role assignment
    for group in Group.objects.prefetch_related('user_set').all():
        user_list = list(group.user_set.all())
        team = Team.objects.filter(group=group).first()
        if not team:
            logger.warning(f'Data migration could not find team by name {group.name}')
            continue

        if user_list:
            give_permissions(apps, member_rd, users=user_list, object_id=team.id, content_type_id=member_rd.content_type_id)


def filter_mismatched_assignments(assignment_qs):
    """
    Filter assignment queryset to find mismatched assignments.
    Works with either RoleUserAssignment or RoleTeamAssignment queryset.

    Only finds: Role has content_type (specific), assignment doesn't (global)
    This is the only mismatch case we repair - creates a global version of the role.
    """
    return assignment_qs.select_related('role_definition').filter(
        role_definition__content_type__isnull=False,
        content_type__isnull=True
    )


def get_all_mismatched_assignments(apps):
    """
    Get all mismatched role assignments (both user and team).
    Returns an iterable chain of all mismatched assignments.
    """
    RoleUserAssignment = apps.get_model('dab_rbac', 'RoleUserAssignment')
    RoleTeamAssignment = apps.get_model('dab_rbac', 'RoleTeamAssignment')

    mismatched_user = filter_mismatched_assignments(RoleUserAssignment.objects.all())
    mismatched_team = filter_mismatched_assignments(RoleTeamAssignment.objects.all())

    return chain(mismatched_user, mismatched_team)


def repair_mismatched_role_assignments(apps, schema_editor):
    """
    Repair RoleUserAssignment and RoleTeamAssignment objects where
    the assignment's content_type differs from the role_definition's content_type.

    This can happen when roles are migrated incorrectly, resulting in:
    - Global assignments (content_type=None) on roles with a specific content_type
    - Object-level assignments with a different content_type than the role_definition

    The repair strategy:
    - Find all mismatched assignments using proper NULL-aware queries
    - Create new global role definitions as needed
    - Move the assignments to the new role definitions
    """
    RoleDefinition = apps.get_model('dab_rbac', 'RoleDefinition')

    logger.debug("Finding and repairing mismatched role assignments...")

    # Track newly created global roles by original role ID
    new_global_roles = {}

    # Process all mismatched assignments
    for assignment in get_all_mismatched_assignments(apps):
        rd = assignment.role_definition

        # Skip if assignment has non-null object_id (unexpected)
        if assignment.object_id is not None:
            assignment_type = "user" if hasattr(assignment, 'user') else "team"
            logger.warning(f"Skipping {assignment_type} assignment {assignment.id}: unexpected non-null object_id")
            continue

        # Get or create the global version of this role
        if rd.id not in new_global_roles:
            permissions = list(rd.permissions.all())
            if not permissions:
                logger.warning(f"Skipping role '{rd.name}': no permissions found")
                continue

            # Validate that shared permissions are view-only
            invalid_shared_perms = []
            for perm in permissions:
                api_slug = perm.api_slug if hasattr(perm, 'api_slug') else None
                if api_slug and api_slug.startswith("shared.") and not api_slug.startswith("shared.view_"):
                    invalid_shared_perms.append(api_slug)

            if invalid_shared_perms:
                all_api_slugs = [perm.api_slug if hasattr(perm, 'api_slug') else perm.codename for perm in permissions]
                raise ValueError(
                    f"Role '{rd.name}' contains invalid shared permissions. "
                    f"Shared permissions must be view-only (start with 'shared.view_'). "
                    f"Invalid permissions: {invalid_shared_perms}. "
                    f"All permissions in role: {all_api_slugs}"
                )

            new_role_name = f"{rd.name}_global"

            # Check if a role with this name already exists
            existing_rd = RoleDefinition.objects.filter(name=new_role_name).first()
            if existing_rd:
                # Verify the existing role has the correct content_type (should be None for global)
                if existing_rd.content_type is not None:
                    raise ValueError(
                        f"Role '{new_role_name}' already exists but has content_type={existing_rd.content_type}, "
                        f"expected content_type=None for global role"
                    )
                logger.info(f"Using existing global role '{new_role_name}'")
                new_rd = existing_rd
            else:
                permission_codenames = [perm.codename for perm in permissions]
                logger.info(f"Creating new global role '{new_role_name}' with permissions: {permission_codenames}")
                new_rd = RoleDefinition.objects.create(
                    name=new_role_name,
                    content_type=None,
                    managed=False,
                    description=f"{rd.description} (Auto-fixed from {rd.name})"
                )
                new_rd.permissions.set(permissions)

            new_global_roles[rd.id] = new_rd

        # Move assignment to new role
        new_rd = new_global_roles[rd.id]

        # Determine actor (user or team)
        if hasattr(assignment, 'user'):
            actor = assignment.user
            actor_name = actor.username
            assignment_type = "user"
        else:
            actor = assignment.team
            actor_name = actor.name
            assignment_type = "team"

        logger.info(f"Moving {assignment_type} assignment {assignment.id} ({assignment_type}={actor_name}) to role '{new_rd.name}'")
        assignment.delete()

        # Use migration-safe utility function instead of calling method on fake model
        give_global_permission_to_actor(new_rd, actor, apps)

    if new_global_roles:
        logger.info(f"Successfully created {len(new_global_roles)} global roles and remediated assignments")
    else:
        logger.info("No mismatched assignments found.")

    logger.info("Role assignment remediation completed")
