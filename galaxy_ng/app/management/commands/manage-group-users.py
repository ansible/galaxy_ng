from galaxy_ng.app.models.auth import Group

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for creating groups
    """

    help = "Add or remove users from an access group"

    def add_arguments(self, parser):
        parser.add_argument("users", nargs="+")
        parser.add_argument("group")
        parser.add_argument(
            "--remove",
            action="store_true",
            help="Remove users from group",
            default=False,
            required=False,
        )

    def handle(self, *args, **options):
        group_name = options["group"]
        try:
            group = Group.objects.get(name=group_name)
        except User.DoesNotExist:
            self.stdout.write("Group '{}' not found. Skipping.".format(group_name))
        else:
            for username in options["users"]:
                try:
                    user = User.objects.get(username=username)
                except User.DoesNotExist:
                    self.stdout.write("User '{}' not found. Skipping.".format(username))
                    continue
                if options["remove"]:
                    user.groups.remove(group)
                else:
                    user.groups.add(group)
                user.save()
                self.stdout.write(
                    "{} group '{}' {} user '{}'".format(
                        ("Removed" if options["remove"] else "Assigned"),
                        group_name,
                        ("from" if options["remove"] else "to"),
                        username,
                    )
                )
