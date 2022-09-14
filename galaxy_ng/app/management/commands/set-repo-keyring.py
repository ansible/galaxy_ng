import os
import sys
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from pulp_ansible.app.models import AnsibleRepository
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES
from pulpcore.plugin.tasking import dispatch


class Command(BaseCommand):
    """This command sets keyring to repository.

    Keyring must be a GPG keyring on the filesystem, default path: /etc/pulp/certs/

    Example:

    django-admin set-repo-keyring --keyring=galaxy.kbx --repository=<repo_name>
    """

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(message))

    def add_arguments(self, parser):
        parser.add_argument( "--gpgkey", type=str, help="Keyring", required=True)
        parser.add_argument("--repository", type=str, help="Repository name", required=True)
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="Skip confirmation",
            default=False,
            required=False,
        )

    def handle(self, *args, **options):

        repository = options["repository"].strip()
        keyring = options["keyring"].strip()

        try:
            repo = AnsibleRepository.objects.get(name=repository)
        except AnsibleRepository.DoesNotExist:
            self.echo(f"Repository {repository} does not exist", self.style.ERROR)
            sys.exit(1)

        certs_dir = settings.get("ANSIBLE_CERTS_DIR", "/etc/pulp/certs")
        keyring_path = os.path.join(certs_dir, keyring)
        if not os.path.exists(keyring_path):
            self.echo(f"Keyring {keyring_path} does not exist", self.style.ERROR)
            sys.exit(1)

        if not options["yes"]:
            confirm = input(
                f"This will set keyring to {keyring} for {repository} repository, " "Proceed? (Y/n)"
            ).lower()
            while True:
                if confirm not in ("y", "n", "yes", "no"):
                    confirm = input('Please enter either "y/yes" or "n/no": ')
                    continue
                if confirm in ("y", "yes"):
                    break
                else:
                    self.echo("Process canceled.")
                    return

        task = dispatch(
            set_repo_keyring,
            kwargs={"repo_id": repo.pk, "keyring": keyring},
            exclusive_resources=[repo],
        )

        while task.state not in TASK_FINAL_STATES:
            time.sleep(1)
            task.refresh_from_db()

        self.echo(f"Process {task.state}")

        if task.state == TASK_STATES.FAILED:
            self.echo(f"Task failed with error: {task.error}", self.style.ERROR)
            sys.exit(1)

        if AnsibleRepository.objects.get(pk=repo.pk).keyring == keyring:
            self.echo(f"Keyring {keyring} set successfully to {repository} repository")


def set_repo_keyring(repo_id, gpgkey):
    """Set keyring for repository"""

    with transaction.atomic():
        repo = AnsibleRepository.objects.get(pk=repo_id)
        repo.gpgkey = gpgkey
        repo.save()
