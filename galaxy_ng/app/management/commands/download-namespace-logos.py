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

    def add_arguments(self, parser):
        parser.add_argument("--namespace", help="find and sync only this namespace name")
        parser.add_argument(
            "--sha-report",
            default=False,
            action="store_true",
            required=False,
            help="report the number of namespaces with avatar_url but missing avatar_sha256",
            dest="sha_report",
        )
        parser.add_argument(
            "--only-missing-sha",
            default=False,
            action="store_true",
            required=False,
            help="When set it will limit the logo download only to those namespaces missing sha",
            dest="only_missing_sha",
        )

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(message))

    def handle(self, *args, **options):
        # all namespaces having avatar_url must have avatar_sha256 set
        # query for namespaces missing avatar_sha256
        ns_missing_avatar_sha = Namespace.objects.filter(
            _avatar_url__isnull=False,
            last_created_pulp_metadata__avatar_sha256__isnull=True
        )
        if ns_missing_avatar_sha:
            self.echo(
                f"{ns_missing_avatar_sha.count()} Namespaces missing avatar_sha256",
                self.style.ERROR
            )
            self.echo(", ".join(ns_missing_avatar_sha.values_list("name", flat=True)))
        else:
            self.echo("There are no namespaces missing avatar_sha256!")

        if options["sha_report"]:  # --sha-report indicated only report was requested
            return

        self.echo("Proceeding with namespace logo downloads")

        kwargs = {
            'namespace_name': options['namespace'],
            'only_missing_sha': options['only_missing_sha'],
        }

        task = dispatch(
            download_all_logos,
            kwargs=kwargs,
            exclusive_resources=list(AnsibleRepository.objects.all()),
        )

        while task.state not in TASK_FINAL_STATES:
            time.sleep(1)
            task.refresh_from_db()

        self.echo(f"Process {task.state}")

        if task.state == TASK_STATES.FAILED:
            self.echo(f"Task failed with error: {task.error}", self.style.ERROR)
            sys.exit(1)


def download_all_logos(namespace_name=None, only_missing_sha=False):
    """Force logo downloads.
    namespace: limit to specified namespace (or list of namespaces)
    only_missing_sha: Limit to namespaces having avatar_url but missing avatar_sha256
    """
    if namespace_name:
        namespaces = namespace_name.split(",")
        qs = Namespace.objects.filter(name__in=namespaces)
    else:
        qs = Namespace.objects.all()

    if only_missing_sha:
        qs = qs.filter(
            _avatar_url__isnull=False,
            last_created_pulp_metadata__avatar_sha256__isnull=True
        )

    for namespace in qs:
        download_logo = False
        if namespace._avatar_url:
            download_logo = True

        _create_pulp_namespace(namespace.pk, download_logo=download_logo)
