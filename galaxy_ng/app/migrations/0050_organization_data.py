from django.conf import settings
from django.db import migrations
from django.utils import timezone


def create_default_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Organization = apps.get_model("galaxy", "Organization")

    now = timezone.now()
    org = Organization.objects.using(db_alias).create(
        name=settings.DEFAULT_ORGANIZATION_NAME,
        description="A default organization.",
        created_on=now,
        modified_on=now,
    )

    schema_editor.execute(
        """
        INSERT INTO galaxy_team (name, description, created_on, modified_on, group_id, organization_id)
        SELECT grp.name, '', now(), now(), grp.id, %s
        FROM auth_group AS grp
    """,
        (org.id,),
    )


def delete_default_organization(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    Team = apps.get_model("galaxy", "Team")
    Organization = apps.get_model("galaxy", "Organization")

    Team.objects.using(db_alias).delete()

    Organization.objects.using(db_alias).filter(name=settings.DEFAULT_ORGANIZATION_NAME).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0049_organization"),
    ]

    operations = [
        migrations.RunPython(
            code=create_default_organization,
            reverse_code=delete_default_organization,
        )
    ]
