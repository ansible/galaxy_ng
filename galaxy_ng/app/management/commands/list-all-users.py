from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for listing all users
    """

    help = 'List all users'

    def handle(self, *args, **options):
        users = User.objects.all()

        if not users.exists():
            self.stdout.write("No users found")
        else:
            for user in users:
                self.stdout.write(f"Username: {user.username}, Email: {user.email}, ID: {user.id}")
