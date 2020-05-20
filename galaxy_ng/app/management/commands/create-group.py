from galaxy_ng.app.models.auth import Group

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for creating groups
    """

    help = 'Create an access group, and optionally assign it to one or more users'

    def add_arguments(self, parser):
        parser.add_argument('groups', nargs='+')
        parser.add_argument(
            '--users',
            default=[],
            nargs='*',
            help='Assign the group(s) to one or more users'
        )

    def handle(self, *args, **options):
        for group_name in options['groups']:
            group, created = Group.objects.get_or_create(name=group_name)
            if created:
                self.stdout.write("Created group '{}'".format(group_name))
            else:
                self.stdout.write("Group '{}' already exists".format(group_name))

            for username in options['users']:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    self.stdout.write("User '{}' not found. Skipping.".format(username))
                    continue
                user.groups.add(group)
                user.save()
                self.stdout.write("Assigned group '{}' to user '{}'".format(group_name, username))
