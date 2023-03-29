import sys
import time
import django_guid

from django.core.management.base import BaseCommand
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.tasks.namespaces import _create_pulp_namespace

# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


class Command(BaseCommand):
    """
    Iterates through every namespace and downloads the logo for it, if one
    doesn't exist
    """

    help = 'Download namespace logos.'

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(message))

    def handle(self, *args, **options):

        task = dispatch(
            download_all_logos,
            exclusive_resources=list(AnsibleRepository.objects.all()),
        )

        while task.state not in TASK_FINAL_STATES:
            time.sleep(1)
            task.refresh_from_db()

        self.echo(f"Process {task.state}")

        if task.state == TASK_STATES.FAILED:
            self.echo(f"Task failed with error: {task.error}", self.style.ERROR)
            sys.exit(1)


def download_all_logos():
    for namespace in Namespace.objects.all():
        download_logo = False
        if namespace._avatar_url:
            download_logo = True

        _create_pulp_namespace(namespace.pk, download_logo=download_logo)
