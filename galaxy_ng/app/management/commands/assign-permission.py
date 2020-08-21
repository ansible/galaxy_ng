from galaxy_ng.app.models.auth import Group

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import BaseCommand, CommandError
from django.core.exceptions import ObjectDoesNotExist

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for assigning permissions to groups.

    Example:

    assign-permission admins galaxy.add_namespace galaxy.change_namespace
    """

    help = 'Assign one or more permissions to a group'

    def valid_group(self, group):
        try:
            return Group.objects.get(name=group)
        except ObjectDoesNotExist:
            raise CommandError(
                'Group {} does not exist. Please provide a valid '
                'group name.'.format(group))

    def valid_permission(self, permission):
        try:
            app_label, codename = permission.split('.', 1)
        except ValueError:
            raise CommandError(
                "Invalid permission format for {}. "
                "Expecting 'app_label.codename'.".format(permission)
            )
        try:
            return Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename)
        except ObjectDoesNotExist:
            raise CommandError(
                "Permission {} not found. Please provide a valid "
                "permission in the form 'app_label.codename'".format(
                    permission))

    def add_arguments(self, parser):
        parser.add_argument('group', type=self.valid_group)
        parser.add_argument(
            'permissions',
            nargs='+',
            type=self.valid_permission
        )

    def handle(self, *args, **options):
        group = options['group']
        for perm in options['permissions']:
            group.permissions.add(perm.id)
        self.stdout.write("Assigned requested permission to "
                          "group '{}'".format(group.name))
