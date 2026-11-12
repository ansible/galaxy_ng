from django.db import migrations


STALE_INDEXES = [
    "core_userrole_content_type_id_a2ff8402",
    "core_userrole_domain_id_f78b1c11",
    "core_userrole_role_id_8272b20d",
    "core_userrole_user_id_aca63c51",
    "core_userro_content_5c0477_idx",
    "core_grouprole_content_type_id_a80c1cfc",
    "core_grouprole_domain_id_9644db4b",
    "core_grouprole_group_id_09264d71",
    "core_grouprole_role_id_3c2c3564",
    "core_groupr_content_ea7d37_idx",
]

drop_sql = "\n".join(f"DROP INDEX IF EXISTS {idx};" for idx in STALE_INDEXES)

create_sql = """
CREATE INDEX IF NOT EXISTS core_userrole_content_type_id_a2ff8402 ON core_userrole (content_type_id);
CREATE INDEX IF NOT EXISTS core_userrole_domain_id_f78b1c11 ON core_userrole (domain_id);
CREATE INDEX IF NOT EXISTS core_userrole_role_id_8272b20d ON core_userrole (role_id);
CREATE INDEX IF NOT EXISTS core_userrole_user_id_aca63c51 ON core_userrole (user_id);
CREATE INDEX IF NOT EXISTS core_userro_content_5c0477_idx ON core_userrole (content_type_id, object_id);
CREATE INDEX IF NOT EXISTS core_grouprole_content_type_id_a80c1cfc ON core_grouprole (content_type_id);
CREATE INDEX IF NOT EXISTS core_grouprole_domain_id_9644db4b ON core_grouprole (domain_id);
CREATE INDEX IF NOT EXISTS core_grouprole_group_id_09264d71 ON core_grouprole (group_id);
CREATE INDEX IF NOT EXISTS core_grouprole_role_id_3c2c3564 ON core_grouprole (role_id);
CREATE INDEX IF NOT EXISTS core_groupr_content_ea7d37_idx ON core_grouprole (content_type_id, object_id);
"""


class Migration(migrations.Migration):
    dependencies = [
        ('galaxy', '0059_delete_system_auditor_role_definition'),
    ]

    operations = [
        migrations.RunSQL(
            sql=drop_sql,
            reverse_sql=create_sql,
        ),
    ]
