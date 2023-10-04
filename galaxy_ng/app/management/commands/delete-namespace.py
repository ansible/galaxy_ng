import sys
import time
import django_guid

from django.core.management.base import BaseCommand
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.models import AnsibleNamespace
from pulp_ansible.app.models import Collection
from pulp_ansible.app.tasks.deletion import delete_collection
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch

from galaxy_ng.app.models import Namespace

# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


class Command(BaseCommand):
    """
    Iterates through every namespace and downloads the logo for it, if one
    doesn't exist
    """

    help = 'Download namespace logos.'

    def add_arguments(self, parser):
        parser.add_argument("namespace_name", help="delete this namespace name")
        parser.add_argument(
            "--delete-collections", help="delete the collections too", action="store_true"
        )

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(message))

    def handle(self, *args, **options):

        namespace_name = options['namespace_name']
        delete_collections = options['delete_collections']

        namespace = Namespace.objects.filter(name=namespace_name).first()
        if not namespace:
            raise Exception(f'no such namespace exists')

        # 1. Check if there are any collections in the namespace.
        if Collection.objects.filter(namespace=namespace.name).exists():
            if not delete_collections:
                raise Exception(
                    f"Namespace {namespace_name} cannot be deleted because "
                    "there are still collections associated with it."
                )

            # iterate and delete
            for col in Collection.objects.filter(namespace=namespace.name):
                print(col)
                do_delete_collection(col)

        namespace.delete()


def do_delete_collection(collection):
    task = dispatch(
        delete_collection,
        args=(collection.pk,),
        exclusive_resources=list(AnsibleRepository.objects.all()),
    )

    while task.state not in TASK_FINAL_STATES:
        time.sleep(1)
        task.refresh_from_db()

    print(f"Process {task.state}")

    if task.state == TASK_STATES.FAILED:
        print(f"Task failed with error: {task.error}")
        sys.exit(1)
