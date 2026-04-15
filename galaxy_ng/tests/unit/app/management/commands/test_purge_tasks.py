import pytest
import random
import string
from io import StringIO
from typing import Optional
from datetime import datetime, timedelta, timezone

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import TestCase

from pulpcore.plugin.models import Task


class TestPurgeTasksCommand(TestCase):
    def setUp(self):
        super().setUp()

    def _create_tasks(
        self,
        tasks: int,
        finished_at: Optional[str] = None,
        days: Optional[int] = None,
        state="completed"
    ):
        if finished_at:
            _datetime = datetime.fromisoformat(finished_at)

        if days:
            _datetime = datetime.now(timezone.utc) - timedelta(days=days)

        rand_str = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        created_pks = []
        for i in range(tasks):
            task = Task.objects.create(
                name=f"custom.task.{i}.{rand_str}",
                state=state,
            )
            created_pks.append(task.pk)
        # pulpcore 3.105+ has DB triggers that force pulp_created=clock_timestamp()
        # on INSERT and prevent UPDATE of pulp_created. Use session_replication_role
        # to temporarily disable all triggers so we can backdate tasks for testing.
        with connection.cursor() as cursor:
            cursor.execute("SET session_replication_role = 'replica'")
        try:
            Task.objects.filter(pk__in=created_pks).update(pulp_created=_datetime)
        finally:
            with connection.cursor() as cursor:
                cursor.execute("SET session_replication_role = 'origin'")

    def _assert_tasks(self, num_tasks: int):
        self.assertEqual(Task.objects.count(), num_tasks)

    def test_must_specify_days_or_finished_before(self):
        out = StringIO()
        err = StringIO()
        with self.assertRaisesMessage(
            CommandError,
            "You must provide either --finished-before or --days-before.",
        ):
            call_command("purge-tasks", stdout=out, stderr=err)

    def test_dry_run_does_nothing(self):
        self._create_tasks(10, days=10)
        self._assert_tasks(10)

        out = StringIO()
        with pytest.raises(SystemExit) as excinfo:
            call_command("purge-tasks", "--days-before", "10", "--dry-run", stdout=out)

        assert excinfo.value.code == 0

        self.assertIn(
            "--- TOTAL TASKS 10 ---",
            out.getvalue(),
        )

        self._assert_tasks(10)

    def test_days_before_param(self):
        self._create_tasks(100, days=15)  # should be deleted
        self._create_tasks(10, days=14)  # should persist

        self._assert_tasks(110)
        call_command("purge-tasks", "--days-before", "15")

        self._assert_tasks(10)

    def test_finished_before_param(self):
        self._create_tasks(100, finished_at="2025-10-15")  # should be deleted
        self._create_tasks(10, finished_at="2025-10-16")  # should persist

        self._assert_tasks(110)

        call_command("purge-tasks", "--finished-before", "2025-10-16")

        self._assert_tasks(10)

    def test_delete_only_finished_tasks(self):
        inprogress_states = ("running", "waiting", "pending")
        finished_states = ("completed", "failed", "skipped", "canceled")
        task_states = inprogress_states + finished_states
        days = 10

        for state in task_states:
            self._create_tasks(10, days=days, state=state)

        self._assert_tasks(days * len(task_states))

        call_command("purge-tasks", "--days-before", "5")

        self._assert_tasks(days * len(inprogress_states))
