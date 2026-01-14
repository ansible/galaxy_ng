from gettext import gettext as _
from datetime import datetime, timedelta, timezone
import uuid

import django_guid
from django.core.management.base import BaseCommand, CommandError
from django.db.models.deletion import ProtectedError
from django.utils import timezone as django_timezone
from django.utils.termcolors import make_style

from pulpcore.plugin.models import Task


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(str(uuid.uuid4()))

DELETE_LIMIT = 1000


# borrowed from https://github.com/pulp/pulpcore/blob/main/pulpcore/app/tasks/purge.py
class Command(BaseCommand):
    """
    Django management command for purging completed tasks from the system.

    Args:
        finished-before (Optional[DateTime]): Earliest finished-time date to NOT purge.
        days-before (Optional[int]): Earliest finished-time days to NOT purge.
            (alternative to --finished-before)
        dry-run (Optional[bool]): Do NOT delete anything, only display number of tasks to delete.

    Example:
        django-admin purge-tasks --finished-before 2025-10-16 --dry-run
        django-admin purge-tasks --finished-before 2025-10-16
        django-admin purge-tasks --finished-before "2025-10-15T14:30:00"
        django-admin purge-tasks --days-before 30
    """

    help = _("Purge finished tasks.")

    def add_arguments(self, parser):
        parser.add_argument(
            "--finished-before", dest="finished-before", type=datetime.fromisoformat,
            help=_("Tasks with this date and older will be purged from the system"),
        )
        parser.add_argument(
            "--days-before",
            dest="days-before",
            type=int,
            help=_("Tasks with this date and older than this days will be purged from the system"),
        )
        parser.add_argument(
            "--dry-run",
            dest="dry-run",
            action="store_true",
            help=_("Do not delete anything.")
        )

    def handle(self, *args, **options):
        finished_before = options.get("finished-before")
        days_before = options.get("days-before")
        dry_run = options.get("dry-run")

        # Validation
        if finished_before and days_before:
            raise CommandError("Use only one of --finished-before or --days-before, not both.")

        if not finished_before and not days_before:
            raise CommandError("You must provide either --finished-before or --days-before.")

        if days_before:
            finished_before_dt = datetime.now(timezone.utc) - timedelta(days=days_before)

        if finished_before:
            finished_before_dt = django_timezone.make_aware(
                finished_before,
                timezone=django_timezone.utc
            )

        states = ("completed", "failed", "skipped", "canceled")
        candidate_qs = Task.objects.filter(pulp_created__lt=finished_before_dt, state__in=states)

        self.expected_total = candidate_qs.count()
        self.stdout.write(f"--- TOTAL TASKS {self.expected_total} ---")

        if dry_run or self.expected_total == 0:
            exit(0)

        pks_failed = []
        tasks_deleted = 0

        # Our delete-query is going to deal with "the first DELETE_LIMIT tasks that match our
        # criteria", looping until we've deleted everything that fits our parameters
        continue_deleting = True

        while continue_deleting:
            # Get a list of candidate objects to delete
            candidate_pks = candidate_qs.exclude(pk__in=pks_failed).values_list("pk", flat=True)
            pk_list = list(candidate_pks[:DELETE_LIMIT])

            # Try deleting the objects in bulk
            try:
                task_list = Task.objects.filter(pk__in=pk_list)

                units_deleted, details = task_list.delete()
                tasks_deleted += units_deleted
                self._deleting_progress(tasks_deleted)

                continue_deleting = units_deleted > 0
            except ProtectedError:
                # If there was at least one object that couldn't be deleted, then
                # loop through the candidate objects and delete them one-by-one
                for pk in pk_list:
                    try:
                        obj = Task.objects.get(pk=pk)
                        count, details = obj.delete()
                        tasks_deleted += count
                        self._deleting_progress(tasks_deleted)
                    except ProtectedError as e:
                        # Object could not be deleted due to foreign key constraint.
                        # Log the details of the object.
                        pks_failed.append(pk)
                        self._warning(e)

    def _warning(self, message: str):
        warning_style = make_style(fg="yellow", opts=("bold",))
        self.stdout.write(warning_style(f"⚠️ {message}"))

    def _deleting_progress(self, tasks_deleted):
        self.stdout.write(f"--- deleted {tasks_deleted}/{self.expected_total} ---")
