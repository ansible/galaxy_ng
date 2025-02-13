from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for listing all users.
    """
    help = "Lists all registered users."

    def handle(self, *args, **options):
        users = User.objects.all()

        if not users:
            self.stdout.write("No users found.")
            return

        for user in users:
            self.stdout.write(f"{user.username} (ID: {user.id})")
