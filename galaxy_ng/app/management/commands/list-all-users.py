from django.contrib.auth import get_user_model
from django.core.management import BaseCommand


class Command(BaseCommand):
    """
    Django management command for listing all users
    """

    help = 'List all users in the system'

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()

        if not users:
            self.stdout.write("No users found")
            return

        self.stdout.write(f"Found {users.count()} user(s):")
        for user in users:
            self.stdout.write(f"  - {user.username}")
