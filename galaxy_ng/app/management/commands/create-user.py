from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from django.core.management import CommandError

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for creating a user
    """

    help = 'Create a user'

    def add_arguments(self, parser):
        parser.add_argument('--user', metavar='USER', dest='username',
                            help='user name', required=True)

    def handle(self, *args, **options):
        username = options['username']
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            try:
                user = User.objects.create(username=username)
                user.save()
            except Exception as e:
                raise CommandError("Could not create user: {}".format(e))

            self.stdout.write("Created user '{}'".format(username))

        self.stdout.write("User '{}' already exists".format(username))
