import logging

from django.db import migrations
from ansible_base.rbac.migrations._utils import give_permissions


logger = logging.getLogger(__name__)


def remove_galaxy_team_member_role(apps, schema_editor):
    """
    Migrate all role assignments from "Galaxy Team Member" to "Team Member".

    This migration consolidates two redundant role names that were serving the same purpose.
    It migrates all user assignments, team assignments, and object roles from the old
    "Galaxy Team Member" role to the standardized "Team Member" role, then deletes
    the old role definition.
    """
    # Get the RoleDefinition model from django-ansible-base
    RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

    # Find the old role we want to migrate away from
    # Using .first() returns None if not found, which is safe
    galaxy_team_member_role = RoleDefinition.objects.filter(name="Galaxy Team Member").first()

    # Find the target role we want to migrate to
    # This role should already exist in the system
    team_member_role = RoleDefinition.objects.filter(name="Team Member").first()

    # Only run the migration if the old role exists
    # If it doesn't exist, this is likely a new installation or the migration already ran
    if galaxy_team_member_role:
        # Migrate all user assignments from Galaxy Team Member to Team Member
        # We iterate through all ObjectRoles (which track which objects have this role)
        for galaxy_obj_role in galaxy_team_member_role.object_roles.all():
            # Get all users who have the Galaxy Team Member role for this object
            galaxy_users = set(galaxy_obj_role.users.all())

            # Skip this object if no users have the role
            if not galaxy_users:
                continue

            # Get the corresponding Team Member ObjectRole for this object
            # This should already exist because Team Member is a pre-created role

            # Get the object ID from the galaxy role's object role
            galaxy_role_obj_id = galaxy_obj_role.object_id

            # Get the corresponding Team Member ObjectRole for the same object
            # It might not exist yet if only Galaxy Team Member was assigned
            team_member_obj_role = team_member_role.object_roles.filter(
                object_id=galaxy_role_obj_id
            ).first()

            # If the Team Member ObjectRole exists, check for existing users to avoid duplicates
            if team_member_obj_role:
                # Get the users who already have the Team Member role for this object
                current_users = set(team_member_obj_role.users.all())

                # Calculate which users need to be migrated (those who don't already have Team Member)
                # This prevents duplicate assignments if a user somehow has both roles
                new_users = galaxy_users - current_users
            else:
                # No Team Member ObjectRole exists yet, so all galaxy_users need migration
                new_users = galaxy_users

            # Skip if all users already have the Team Member role
            if not new_users:
                continue

            # Log the migration for debugging and audit purposes
            logger.info(
                f"Copying permissions from old member role for users: {new_users}, team_id={galaxy_obj_role.object_id}"
            )

            # Assign the Team Member role to users who only had Galaxy Team Member
            # give_permissions is the migration utility that properly creates all necessary records
            give_permissions(
                apps,  # The apps registry for accessing models
                team_member_role,  # The role to assign
                users=new_users,  # The users to assign it to
                teams=[],  # No team assignments in this call
                object_id=galaxy_obj_role.object_id,  # The object this role applies to
                content_type_id=galaxy_obj_role.content_type_id,  # The type of object
            )

        # Clean up: Delete all ObjectRoles for the Galaxy Team Member role
        # This removes the meta-records that track role availability
        for galaxy_obj_role in galaxy_team_member_role.object_roles.all():
            logger.info(f"Deleting old object member-role {galaxy_obj_role.id}")
            galaxy_obj_role.delete()

        # Finally, delete the Galaxy Team Member role definition itself
        # This removes the role from the system completely
        logger.info(f"Deleting Galaxy Team Member role id={galaxy_team_member_role.id}")
        galaxy_team_member_role.delete()


class Migration(migrations.Migration):
    # This migration depends on:
    # 1. The previous galaxy_ng migration (0057) which sets up organizations
    # 2. DAB RBAC migration (0003) which establishes the RBAC permission system
    dependencies = [
        ("galaxy", "0057_alter_organization_created_and_more"),
        ("dab_rbac", "0003_alter_dabpermission_codename_and_more"),
    ]

    # This migration MUST run before DAB RBAC migration 0004
    # Because 0004 adds remote permissions and we need to clean up old roles first
    run_before = [("dab_rbac", "0004_remote_permissions_additions")]

    # The migration operations to execute
    operations = [
        # Run our Python function forward, but do nothing on reverse (noop)
        # This is a data migration, so we can't easily reverse it
        migrations.RunPython(remove_galaxy_team_member_role, migrations.RunPython.noop),
    ]
