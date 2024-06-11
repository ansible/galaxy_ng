import importlib
from django.core.management.base import BaseCommand, CommandError
from datetime import timedelta
from django.utils.timezone import now


class Command(BaseCommand):
    """Schedules a task for execution using Pulp Tasking System."""

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            required=True,
            type=str,
            help="Unique str identifier for scheduled task e.g: make_sandwich"
        )
        parser.add_argument(
            '--path',
            required=True,
            help="Importable path for the callable e.g: galaxy_ng.app.foo.bar"
        )
        parser.add_argument(
            '--interval',
            required=True,
            type=int,
            help="Interval in minutes"
        )
        parser.add_argument(
            '--force',
            action="store_true",
            default=False,
            help="Override existing scheduled task with the same identifier"
        )

    def handle(self, *args, **options):
        # bypass pulp bad import check because the model is not exposed on plugins path
        TaskSchedule = importlib.import_module("pulpcore.app.models").TaskSchedule
        identifier = options["id"]
        function_path = options["path"]
        dispatch_interval = timedelta(minutes=options["interval"])
        next_dispatch = now() + dispatch_interval

        if existing := TaskSchedule.objects.filter(name=identifier):
            if options["force"]:
                existing.delete()
            else:
                raise CommandError(
                    f"{identifier} is already scheduled, use --force to override it."
                )

        task = TaskSchedule(
            name=identifier,
            task_name=function_path,
            dispatch_interval=dispatch_interval,
            next_dispatch=next_dispatch
        )
        task.save()
        self.stdout.write(
            f"{task.name} scheduled for every {dispatch_interval} minutes. "
            f"next execution on: {next_dispatch}"
        )
