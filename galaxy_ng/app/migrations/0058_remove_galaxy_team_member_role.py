import logging

from django.db import migrations
from ansible_base.rbac.migrations._utils import give_permissions


logger = logging.getLogger(__name__)


def remove_galaxy_team_member_role(apps, schema_editor):
    RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

    galaxy_team_member_role = RoleDefinition.objects.filter(name="Galaxy Team Member").first()
    team_member_role = RoleDefinition.objects.filter(name="Team Member").first()

    if galaxy_team_member_role:
        # Copy any extra permissions from the galaxy version of the role to the shared role
        for galaxy_obj_role in galaxy_team_member_role.object_roles.all():
            galaxy_users = set(galaxy_obj_role.users.all())
            if not galaxy_users:
                continue
            team_member_role_obj_role = team_member_role.object_roles.get(object_id=galaxy_obj_role.object_id)
            current_users = set(team_member_role_obj_role.users.all())
            new_users = galaxy_users - current_users
            if not new_users:
                continue
            logger.info(
                f"Copying permissions from old member role for users: {new_users}, team_id={galaxy_obj_role.object_id}"
            )
            give_permissions(
                apps,
                team_member_role,
                users=new_users,
                teams=[],
                object_id=galaxy_obj_role.object_id,
                content_type_id=galaxy_obj_role.content_type_id,
            )

        # Delete any permissions related to the galaxy team member role
        for galaxy_obj_role in galaxy_team_member_role.object_roles.all():
            logger.info(f"Deleting old object member-role {galaxy_obj_role.id}")
            galaxy_obj_role.delete()

        # Delete the galaxy team member role
        logger.info(f"Deleting Galaxy Team Member role id={galaxy_team_member_role.id}")
        galaxy_team_member_role.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0057_alter_organization_created_and_more"),
        ("dab_rbac", "0003_alter_dabpermission_codename_and_more"),
    ]
    run_before = [("dab_rbac", "0004_remote_permissions_additions")]

    operations = [
        migrations.RunPython(remove_galaxy_team_member_role, migrations.RunPython.noop),
    ]
