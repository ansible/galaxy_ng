from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection


def _applied_names(app='core', migration_name='0001_squashed_0090_char_to_text_field'):
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM django_migrations WHERE app = %s"
            " AND name = %s",
            [app, migration_name],
        )
        return [row[0] for row in cursor.fetchall()]


def _insert(app, name):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied)"
            " VALUES (%s, %s, NOW())",
            [app, name],
        )


def _delete(app, name):
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
            [app, name],
        )


@pytest.mark.django_db
class TestFixSquashedMigrations:

    def test_noop_when_squashed_already_present(self):
        if not _applied_names('core', '0001_squashed_0090_char_to_text_field'):
            _insert('core', "0001_squashed_0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "already recorded" in out.getvalue()

    def test_inserts_squashed_when_individual_applied(self):
        _delete('core', "0001_squashed_0090_char_to_text_field")
        _insert('core', "0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        output = out.getvalue()
        assert "Inserted" in output
        expected = ["0001_squashed_0090_char_to_text_field"]
        assert _applied_names('core', '0001_squashed_0090_char_to_text_field') == expected

    def test_skips_fresh_database(self):
        _delete('core', "0001_squashed_0090_char_to_text_field")
        _delete('core', "0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "nothing to fix" in out.getvalue()
        assert _applied_names('core', '0001_squashed_0090_char_to_text_field') == []

    def test_file_noop_when_squashed_already_present(self):
        if not _applied_names('file', '0001_initial_squashed_0016_add_domain'):
            _insert('file', "0001_initial_squashed_0016_add_domain")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "already recorded" in out.getvalue()

    def test_file_inserts_squashed_when_individual_applied(self):
        _delete('file', "0001_initial_squashed_0016_add_domain")
        _insert('file', "0016_add_domain")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        output = out.getvalue()
        assert "Inserted" in output
        assert "file.0001_initial_squashed_0016_add_domain" in output
        expected = ["0001_initial_squashed_0016_add_domain"]
        assert _applied_names('file', '0001_initial_squashed_0016_add_domain') == expected

    def test_file_skips_fresh_database(self):
        _delete('file', "0001_initial_squashed_0016_add_domain")
        _delete('file', "0016_add_domain")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "nothing to fix" in out.getvalue()
        assert _applied_names('file', '0001_initial_squashed_0016_add_domain') == []
