from django.core.management import BaseCommand
from django.db import connection, transaction
from django.db.migrations.recorder import MigrationRecorder


SQUASHED_MIGRATIONS = [
    {
        "app": "core",
        "squashed": "0001_squashed_0090_char_to_text_field",
        "last_individual": "0090_char_to_text_field",
    },
    {
        "app": "file",
        "squashed": "0001_initial_squashed_0016_add_domain",
        "last_individual": "0016_add_domain",
    },
    {
        "app": "ansible",
        "squashed": "0001_initial_squashed_0040_ansiblerepository_keyring",
        "last_individual": "0040_ansiblerepository_keyring",
    },
]

# A "chained squash" is a newer squash whose `replaces` list includes an older
# squash migration together with individual migrations released since. Django
# can only safely collapse such a squash if ALL its replaced entries are
# recorded in django_migrations — partial application causes migrate to crash.
# See AAP-90575.
CHAINED_SQUASHES = [
    {
        "app": "ansible",
        "squashed": "0001_squashed_0054_split_collection_version_numbers",
        "members": (
            "0001_initial_squashed_0040_ansiblerepository_keyring",
            "0041_alter_collectionversion_collection",
            "0042_ansiblerepository_gpgkey",
            "0043_alter_collectionversionsignature_data",
            "0044_alter_collectionremote_token",
            "0045_downloadlog",
            "0046_add_fulltext_search_fix",
            "0047_ansible_namespace",
            "0048_collectionversionmark",
            "0049_rbac_permissions",
            "0050_crossrepositorycollectionversionindex",
            "0051_cvindex_build",
            "0052_alter_ansiblecollectiondeprecated_content_ptr_and_more",
            "0053_collectiondownloadcount",
            "0054_split_collection_version_numbers",
        ),
    },
]


class Command(BaseCommand):
    """Fix inconsistent migration history caused by squashed migrations.

    When upgrading across versions that introduced squashed migrations
    (e.g. pulpcore 3.85+ for core, pulp_file for file), databases
    migrated with the old version have the individual migration records
    but not the squashed one, which causes InconsistentMigrationHistory.

    This command inserts the missing squashed migration record when the
    individual migrations it replaces are already applied.

    $ django-admin fix-squashed-migrations
    """

    help = "Insert missing squashed-migration records to prevent InconsistentMigrationHistory"

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        recorder.ensure_schema()
        applied = set(recorder.applied_migrations())
        for entry in SQUASHED_MIGRATIONS:
            app = entry["app"]
            if (app, entry["squashed"]) in applied:
                self.stdout.write(f"{app}.{entry['squashed']} already recorded, skipping.")
                continue

            if (app, entry["last_individual"]) not in applied:
                self.stdout.write(
                    f"{app}.{entry['last_individual']} not applied,"
                    " nothing to fix (fresh database)."
                )
                continue

            recorder.record_applied(app, entry["squashed"])
            applied.add((app, entry["squashed"]))
            self.stdout.write(f"Inserted {app}.{entry['squashed']} into django_migrations.")

        for entry in CHAINED_SQUASHES:
            self._repair_chained_squash(recorder, applied, entry)

    def _repair_chained_squash(self, recorder, applied, entry):
        # Django's migration loader requires that a squash migration's `replaces`
        # list is either fully recorded in django_migrations or not at all —
        # a partially-applied replace list causes migrate to crash. This method
        # backfills any missing member records, but only when we can prove the
        # underlying schema changes were actually applied. We use the last member
        # as that proof: Django enforces migration ordering, so if the final
        # migration in the chain is recorded, everything before it must have run
        # (whether individually or via a prior squash). That makes it safe to
        # insert the missing bookkeeping rows without risking a schema gap.
        app = entry["app"]
        members = entry["members"]

        if (app, entry["squashed"]) in applied:
            self.stdout.write(f"{app}.{entry['squashed']} already recorded, skipping.")
            return

        applied_members = {name for a, name in applied if a == app and name in members}

        if members[-1] not in applied_members:
            # Last member not applied — we can't confirm the schema exists for
            # the missing migrations, so inserting fake records could silently
            # leave tables absent from the database.
            if applied_members:
                self.stdout.write(
                    f"{app.capitalize()} chained squash has a partial history "
                    f"({len(applied_members)}/{len(members)} members applied) but "
                    "the last member is absent; cannot safely repair automatically."
                )
            return

        missing = [m for m in members if m not in applied_members]

        with transaction.atomic():
            for migration in missing:
                recorder.record_applied(app, migration)
            recorder.record_applied(app, entry["squashed"])

        if missing:
            self.stdout.write(
                f"Inserted {len(missing)} missing {app} member record(s) and "
                f"{app}.{entry['squashed']} into django_migrations."
            )
        else:
            self.stdout.write(f"Inserted {app}.{entry['squashed']} into django_migrations.")
