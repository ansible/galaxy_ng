import importlib
from io import StringIO
from django.core.management import call_command, CommandError
from django.test import TestCase
from datetime import timedelta


def make_sandwich():
    """make a sandwich task"""
    return "<bread>(picles)(lettuce)(onion)(tomato)(tofu)</bread>"


FUNC_NAME = make_sandwich.__name__
FUNC_PATH = f"{make_sandwich.__module__}.{FUNC_NAME}"


class TestTaskScheduler(TestCase):
    def setUp(self):
        super().setUp()

    def test_command_output(self):
        with self.assertRaisesMessage(
            CommandError, 'Error: the following arguments are required: --id, --path, --interval'
        ):
            call_command('task-scheduler')

    def test_schedule_a_task(self):
        out = StringIO()
        call_command(
            'task-scheduler',
            '--id',
            FUNC_NAME,
            '--path',
            FUNC_PATH,
            '--interval',
            '45',
            stdout=out
        )
        self.assertIn(
            f"{FUNC_NAME} scheduled for every 0:45:00 minutes.",
            out.getvalue()
        )
        TaskSchedule = importlib.import_module("pulpcore.app.models").TaskSchedule
        task = TaskSchedule.objects.get(name=FUNC_NAME)
        assert task.dispatch_interval == timedelta(minutes=45)
        assert task.task_name == FUNC_PATH
