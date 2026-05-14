from django.core.management import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


SQUASHED_CORE_MIGRATIONS = [
    {
        "squashed": "0001_squashed_0090_char_to_text_field",
        "last_individual": "0090_char_to_text_field",
    },
]


class Command(BaseCommand):
    """Fix inconsistent migration history caused by pulpcore squashed migrations.

    When upgrading from pulpcore <3.85 to 3.85+, the individual core
    migrations 0001-0090 are replaced by a single squashed migration.
    Databases migrated with the old version have the individual records
    but not the squashed one, which causes InconsistentMigrationHistory.

    This command inserts the missing squashed migration record when the
    individual migrations it replaces are already applied.

    $ django-admin fix-squashed-migrations
    """

    help = "Insert missing squashed-migration records to prevent InconsistentMigrationHistory"

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        recorder.ensure_schema()
        applied = recorder.applied_migrations()
        for entry in SQUASHED_CORE_MIGRATIONS:
            if ("core", entry["squashed"]) in applied:
                self.stdout.write(
                    f"core.{entry['squashed']} already recorded, skipping."
                )
                continue

            if ("core", entry["last_individual"]) not in applied:
                self.stdout.write(
                    f"core.{entry['last_individual']} not applied,"
                    " nothing to fix (fresh database)."
                )
                continue

            recorder.record_applied("core", entry["squashed"])
            self.stdout.write(
                f"Inserted core.{entry['squashed']} into django_migrations."
            )
