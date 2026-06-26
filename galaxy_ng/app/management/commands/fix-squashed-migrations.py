from django.core.management import BaseCommand
from django.db import connection
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
        applied = recorder.applied_migrations()
        for entry in SQUASHED_MIGRATIONS:
            app = entry["app"]
            if (app, entry["squashed"]) in applied:
                self.stdout.write(
                    f"{app}.{entry['squashed']} already recorded, skipping."
                )
                continue

            if (app, entry["last_individual"]) not in applied:
                self.stdout.write(
                    f"{app}.{entry['last_individual']} not applied,"
                    " nothing to fix (fresh database)."
                )
                continue

            recorder.record_applied(app, entry["squashed"])
            self.stdout.write(
                f"Inserted {app}.{entry['squashed']} into django_migrations."
            )
