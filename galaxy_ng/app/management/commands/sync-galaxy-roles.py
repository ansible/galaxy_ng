import django_guid
from django.core.management.base import BaseCommand
from galaxy_ng.app.api.v1.tasks import legacy_sync_from_upstream


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


class Command(BaseCommand):
    """
    Iterates through api/v1/roles and sync all roles found.
    """

    help = 'Sync upstream roles from [old-]galaxy.ansible.com'

    def add_arguments(self, parser):
        parser.add_argument("--baseurl", default="https://old-galaxy.ansible.com")
        parser.add_argument("--github_user", help="find and sync only this namespace name")
        parser.add_argument("--role_name", help="find and sync only this role name")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--start_page", type=int)

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(message))

    def handle(self, *args, **options):

        # This is the function that api/v1/sync eventually calls in a task ...
        legacy_sync_from_upstream(
            baseurl=options['baseurl'],
            github_user=options['github_user'],
            role_name=options['role_name'],
            limit=options['limit'],
            start_page=options['start_page'],
        )
