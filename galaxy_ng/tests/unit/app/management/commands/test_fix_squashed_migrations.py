from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection


def _applied_names():
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT name FROM django_migrations WHERE app = 'core'"
            " AND name = '0001_squashed_0090_char_to_text_field'"
        )
        return [row[0] for row in cursor.fetchall()]


def _insert(name):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO django_migrations (app, name, applied)"
            " VALUES ('core', %s, NOW())",
            [name],
        )


def _delete(name):
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = 'core' AND name = %s",
            [name],
        )


@pytest.mark.django_db
class TestFixSquashedMigrations:

    def test_noop_when_squashed_already_present(self):
        if not _applied_names():
            _insert("0001_squashed_0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "already recorded" in out.getvalue()

    def test_inserts_squashed_when_individual_applied(self):
        _delete("0001_squashed_0090_char_to_text_field")
        _insert("0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        output = out.getvalue()
        assert "Inserted" in output
        assert _applied_names() == ["0001_squashed_0090_char_to_text_field"]

    def test_skips_fresh_database(self):
        _delete("0001_squashed_0090_char_to_text_field")
        _delete("0090_char_to_text_field")
        out = StringIO()
        call_command("fix-squashed-migrations", stdout=out)
        assert "nothing to fix" in out.getvalue()
        assert _applied_names() == []
