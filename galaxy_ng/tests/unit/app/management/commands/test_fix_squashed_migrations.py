from importlib import import_module
from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder


_fix_squashed_migrations = import_module(
    "galaxy_ng.app.management.commands.fix-squashed-migrations"
)
_ANSIBLE_CHAINED_SQUASH_ENTRY = next(
    entry for entry in _fix_squashed_migrations.CHAINED_SQUASHES if entry["app"] == "ansible"
)
ANSIBLE_CHAINED_SQUASH = _ANSIBLE_CHAINED_SQUASH_ENTRY["squashed"]
ANSIBLE_CHAINED_SQUASH_MEMBERS = _ANSIBLE_CHAINED_SQUASH_ENTRY["members"]


def _applied_names(app="core", migration_name="0001_squashed_0090_char_to_text_field"):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM django_migrations WHERE app = %s AND name = %s",
            [app, migration_name],
        )
        return [row[0] for row in cursor.fetchall()]


def _insert(app, name):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
            [app, name],
        )


def _delete(app, name):
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
            [app, name],
        )


def _delete_ansible_chained_squash_members():
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = %s AND name = ANY(%s)",
            ["ansible", [*ANSIBLE_CHAINED_SQUASH_MEMBERS, ANSIBLE_CHAINED_SQUASH]],
        )


@pytest.mark.django_db
class TestFixSquashedMigrations:
    def test_noop_when_squashed_already_present(self):
        if not _applied_names("core", "0001_squashed_0090_char_to_text_field"):
            _insert("core", "0001_squashed_0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "already recorded" in out.getvalue()

    def test_inserts_squashed_when_individual_applied(self):
        _delete("core", "0001_squashed_0090_char_to_text_field")
        _insert("core", "0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        output = out.getvalue()
        assert "Inserted" in output
        expected = ["0001_squashed_0090_char_to_text_field"]
        assert _applied_names("core", "0001_squashed_0090_char_to_text_field") == expected

    def test_skips_fresh_database(self):
        _delete("core", "0001_squashed_0090_char_to_text_field")
        _delete("core", "0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "nothing to fix" in out.getvalue()
        assert _applied_names("core", "0001_squashed_0090_char_to_text_field") == []

    def test_file_noop_when_squashed_already_present(self):
        if not _applied_names("file", "0001_initial_squashed_0016_add_domain"):
            _insert("file", "0001_initial_squashed_0016_add_domain")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "already recorded" in out.getvalue()

    def test_file_inserts_squashed_when_individual_applied(self):
        _delete("file", "0001_initial_squashed_0016_add_domain")
        _insert("file", "0016_add_domain")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        output = out.getvalue()
        assert "Inserted" in output
        assert "file.0001_initial_squashed_0016_add_domain" in output
        expected = ["0001_initial_squashed_0016_add_domain"]
        assert _applied_names("file", "0001_initial_squashed_0016_add_domain") == expected

    def test_file_skips_fresh_database(self):
        _delete("file", "0001_initial_squashed_0016_add_domain")
        _delete("file", "0016_add_domain")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "nothing to fix" in out.getvalue()
        assert _applied_names("file", "0001_initial_squashed_0016_add_domain") == []

    def test_chained_squash_repairs_members_and_records_squash_atomically(self):
        # When the last member is present, backfill any missing member records
        # and record the squash row itself — all in one transaction.
        _delete_ansible_chained_squash_members()
        _insert("ansible", ANSIBLE_CHAINED_SQUASH_MEMBERS[-1])  # 0054 only

        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)

        assert ANSIBLE_CHAINED_SQUASH in out.getvalue()
        for migration in ANSIBLE_CHAINED_SQUASH_MEMBERS:
            assert _applied_names("ansible", migration) == [migration]
        assert _applied_names("ansible", ANSIBLE_CHAINED_SQUASH) == [ANSIBLE_CHAINED_SQUASH]

    def test_chained_squash_records_squash_row_when_all_members_present(self):
        # All member records already present but squash row missing — just
        # record the squash row without inserting any member records.
        _delete_ansible_chained_squash_members()
        for migration in ANSIBLE_CHAINED_SQUASH_MEMBERS:
            _insert("ansible", migration)

        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)

        assert ANSIBLE_CHAINED_SQUASH in out.getvalue()
        assert "member" not in out.getvalue()
        assert _applied_names("ansible", ANSIBLE_CHAINED_SQUASH) == [ANSIBLE_CHAINED_SQUASH]

    def test_chained_squash_repair_is_idempotent(self):
        _delete_ansible_chained_squash_members()
        _insert("ansible", ANSIBLE_CHAINED_SQUASH_MEMBERS[-1])

        call_command("fix-squashed-migrations", stdout=StringIO())
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)

        assert "already recorded" in out.getvalue()
        assert _applied_names("ansible", ANSIBLE_CHAINED_SQUASH) == [ANSIBLE_CHAINED_SQUASH]

    def test_chained_squash_repair_rolls_back_on_error(self, monkeypatch):
        _delete_ansible_chained_squash_members()
        _insert("ansible", ANSIBLE_CHAINED_SQUASH_MEMBERS[-1])

        original = MigrationRecorder.record_applied

        def fail_on_third_member(recorder, app, name):
            if app == "ansible" and name == ANSIBLE_CHAINED_SQUASH_MEMBERS[2]:
                raise RuntimeError("simulated failure")
            return original(recorder, app, name)

        monkeypatch.setattr(MigrationRecorder, "record_applied", fail_on_third_member)
        out = StringIO()
        with pytest.raises(RuntimeError, match="simulated failure"):
            call_command("fix-squashed-migrations", stdout=out)

        # All writes rolled back — only the original seed remains.
        assert _applied_names("ansible", ANSIBLE_CHAINED_SQUASH) == []
        for migration in ANSIBLE_CHAINED_SQUASH_MEMBERS[:-1]:
            assert _applied_names("ansible", migration) == []

        monkeypatch.undo()
        call_command("fix-squashed-migrations", stdout=StringIO())
        assert _applied_names("ansible", ANSIBLE_CHAINED_SQUASH) == [ANSIBLE_CHAINED_SQUASH]

    def test_chained_squash_warns_on_partial_history_without_last_member(self):
        # Some members present but 0054 is absent — cannot confirm schema
        # exists for the missing migrations, so no automatic repair.
        _delete_ansible_chained_squash_members()
        for migration in ANSIBLE_CHAINED_SQUASH_MEMBERS[:2]:
            _insert("ansible", migration)

        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)

        assert "cannot safely repair" in out.getvalue()
        for migration in ANSIBLE_CHAINED_SQUASH_MEMBERS[2:]:
            assert _applied_names("ansible", migration) == []

    def test_chained_squash_silent_on_fresh_db(self):
        # No members at all — fresh DB, nothing to warn about.
        _delete_ansible_chained_squash_members()

        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)

        assert "cannot safely repair" not in out.getvalue()
        for migration in ANSIBLE_CHAINED_SQUASH_MEMBERS:
            assert _applied_names("ansible", migration) == []
