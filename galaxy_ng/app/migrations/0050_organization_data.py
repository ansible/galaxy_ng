from django.db import migrations
from django.utils import timezone

DEFAULT_ORGANIZATION_NAME = 'Default'

def create_default_org(apps, schema_editor):
    Organization = apps.get_model('galaxy', 'Organization')
    db_alias = schema_editor.connection.alias

    now = timezone.now()
    Organization.objects.using(db_alias).create(
        name=DEFAULT_ORGANIZATION_NAME,
        description='The default organization.',
        created_on=now,
        modified_on=now,
    )

def delete_default_org(apps, schema_editor):
    Organization = apps.get_model('galaxy', 'Organization')
    db_alias = schema_editor.connection.alias

    Organization.objects.using(db_alias).filter(name=DEFAULT_ORGANIZATION_NAME).delete()


ADD_USERS_TO_DEFAULT_GROUP = f"""
INSERT INTO galaxy_organization_users (user_id, organization_id)
SELECT u.id AS user_id,
    (
        SELECT o.id
        FROM galaxy_organization AS o
        WHERE o.name = '{DEFAULT_ORGANIZATION_NAME}'
    ) AS organization_id
FROM galaxy_user AS u;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0049_organization"),
    ]

    operations = [
        migrations.RunPython(code=create_default_org, reverse_code=delete_default_org),
        migrations.RunSQL(sql=ADD_USERS_TO_DEFAULT_GROUP, reverse_sql=migrations.RunSQL.noop),
    ]
