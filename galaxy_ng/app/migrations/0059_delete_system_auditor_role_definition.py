from django.db import migrations
from galaxy_ng.app.migrations._dab_rbac import repair_mismatched_role_assignments


def delete_system_auditor_role_definition(apps, schema_editor):
    """Delete the 'System Auditor' RoleDefinition if it exists."""
    RoleDefinition = apps.get_model("dab_rbac", "RoleDefinition")

    # Delete the System Auditor role definition if it exists
    system_auditor_role = RoleDefinition.objects.filter(name="System Auditor").first()
    if system_auditor_role:
        system_auditor_role.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0058_remove_galaxy_team_member_role"),
        ("dab_rbac", "0003_alter_dabpermission_codename_and_more"),
    ]

    operations = [
        migrations.RunPython(delete_system_auditor_role_definition, migrations.RunPython.noop),
        migrations.RunPython(repair_mismatched_role_assignments, migrations.RunPython.noop),
    ]
