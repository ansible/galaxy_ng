from django.db import migrations


def remove_galaxy_team_member_role(apps, schema_editor):
    RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")
    RoleUserAssignment = apps.get_model("dab_rbac", "RoleUserAssignment")
    RoleTeamAssignment = apps.get_model("dab_rbac", "RoleTeamAssignment")
    ObjectRole = apps.get_model("dab_rbac", "ObjectRole")

    galaxy_team_member_role = RoleDefinition.objects.filter(name="Galaxy Team Member").first()
    team_member_role = RoleDefinition.objects.filter(name="Team Member").first()

    if galaxy_team_member_role:
        RoleUserAssignment.objects.filter(role_definition_id=galaxy_team_member_role.id).update(role_definition_id=team_member_role.id)
        RoleTeamAssignment.objects.filter(role_definition_id=galaxy_team_member_role.id).update(role_definition_id=team_member_role.id)
        ObjectRole.objects.filter(role_definition_id=galaxy_team_member_role.id).update(role_definition_id=team_member_role.id)

        galaxy_team_member_role.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0057_alter_organization_created_and_more"),
        ("dab_rbac", "0003_alter_dabpermission_codename_and_more"),
    ]

    operations = [
        migrations.RunPython(remove_galaxy_team_member_role, migrations.RunPython.noop),
    ]
