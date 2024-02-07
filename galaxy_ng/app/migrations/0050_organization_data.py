from django.db import migrations
from django.utils import timezone

DEFAULT_ORGANIZATION_NAME = "Default"
GROUP_ORG_PREFIX = "org::"
GROUP_TEAM_PREFIX = "team:{0}::"


def upgrade(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Organization = apps.get_model("galaxy", "Organization")
    Group = apps.get_model("galaxy", "Group")

    now = timezone.now()
    org_group = Group.objects.using(db_alias).create(
        name=f"{GROUP_ORG_PREFIX}{DEFAULT_ORGANIZATION_NAME}",
    )
    org = Organization.objects.using(db_alias).create(
        name=DEFAULT_ORGANIZATION_NAME,
        description="The default organization.",
        created_on=now,
        modified_on=now,
        group=org_group,
    )

    schema_editor.execute("""
        INSERT INTO galaxy_team (name, description, created_on, modified_on, group_id, organization_id)
        SELECT grp.name, '', now(), now(), grp.id, %s  
        FROM auth_group AS grp
        WHERE grp.id != %s
    """, (org.id, org.group.id))

    schema_editor.execute("""
        UPDATE auth_group SET name = %s || name WHERE id != %s 
    """, (GROUP_TEAM_PREFIX.format(org.id), org.group.id))

def downgrade(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Organization = apps.get_model("galaxy", "Organization")
    Team = apps.get_model("galaxy", "Team")
    Group = apps.get_model("galaxy", "Group")

    schema_editor.execute("""
        UPDATE auth_group AS grp SET name = team.name
        FROM galaxy_team AS team 
        WHERE grp.id = team.group_id 
    """)

    Team.objects.using(db_alias).delete()

    Organization.objects.using(db_alias).filter(
        name=DEFAULT_ORGANIZATION_NAME
    ).delete()
    Group.objects.using(db_alias).filter(
        name=f"{GROUP_ORG_PREFIX}{DEFAULT_ORGANIZATION_NAME}"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0049_organization"),
    ]

    operations = [
        migrations.RunPython(code=upgrade, reverse_code=downgrade),
    ]
