import django_guid
from django.core.management.base import BaseCommand

from galaxy_ng.app.api.v1.tasks import legacy_role_import


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


class Command(BaseCommand):
    """
    Import a role using the same functions the API uses.
    """

    help = 'Import a role using the same functions the API uses.'

    def add_arguments(self, parser):
        parser.add_argument("--github_user", required=True)
        parser.add_argument("--github_repo", required=True)
        parser.add_argument("--role_name", help="find and sync only this namespace name")
        parser.add_argument("--branch", help="find and sync only this namespace name")
        parser.add_argument("--request_username", help="set the uploader's username")

    def handle(self, *args, **options):
        # This is the same function that api/v1/imports eventually calls ...
        legacy_role_import(
            request_username=options['request_username'],
            github_user=options['github_user'],
            github_repo=options['github_repo'],
            github_reference=options['branch'],
            alternate_role_name=options['role_name'],
        )
