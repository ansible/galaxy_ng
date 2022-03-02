from django.core.management.base import BaseCommand
from django.db import transaction
from pulp_ansible.app.models import AnsibleRepository


class Command(BaseCommand):
    """This command sets retain repo versions for repositories

    Example:

    django-admin set-retain-repo-versions --value=1 --repository=<repo_name>
    django-admin set-retain-repo-versions --value=1 --repository="*"
    django-admin set-retain-repo-versions --value=1 --repository="*" --exclude=<repo_name>
    """

    def echo(self, message):
        self.stdout.write(self.style.SUCCESS(message))

    def add_arguments(self, parser):
        parser.add_argument("--value", type=int, help="Value to set", required=True)
        parser.add_argument("--repository", type=str, help="Repository name", required=True)
        parser.add_argument(
            "--exclude", type=str, help="Repository name to exclude", required=False, default=None
        )
        parser.add_argument(
            "-y",
            "--yes",
            action="store_true",
            help="Skip confirmation",
            default=False,
            required=False,
        )

    def handle(self, *args, **options):

        repository = options["repository"].split(",")
        value = options["value"]
        exclude = options["exclude"].split(",") if options["exclude"] else []

        if "*" in repository:
            repositories = AnsibleRepository.objects.all()
        else:
            repositories = AnsibleRepository.objects.filter(name__in=repository)

        if exclude:
            repositories = repositories.exclude(name__in=exclude)

        repo_list = repositories.values_list("name", flat=True)

        if not options["yes"]:
            confirm = input(
                f"This will set retain_repo_versions to {value} for {len(repo_list)} repositories, "
                f"repo_list[:20]={repo_list[:20]}\n"
                "Proceed? (Y/n)"
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

        with transaction.atomic():
            for repo in repositories:
                repo.retain_repo_versions = value
                repo.save()

        self.echo(
            f"Successfully set retain repo versions to {value} for {len(repo_list)} repositories"
        )
