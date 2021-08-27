from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for deleting a user
    """

    help = 'Delete a user'

    def add_arguments(self, parser):
        parser.add_argument('--user', metavar='USER', dest='username',
                            help='user name', required=True)

    def handle(self, *args, **options):
        username = options['username']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write("User not found")
        else:
            user.delete()
            self.stdout.write("User '{}' deleted".format(username))
