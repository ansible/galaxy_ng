from django.contrib.auth.models import Permission
from django.core.management import BaseCommand
from pulpcore.plugin.models.role import Role
from pulpcore.plugin.util import assign_role

from galaxy_ng.app.models.auth import Group

PE_GROUP_NAME = "system:partner-engineers"
PE_ROLE_NAME = "system:partner-engineers"


class Command(BaseCommand):
    """
    This command creates or updates a partner engineering group
    with a standard set of permissions. Intended to be used for
    settings.GALAXY_DEPLOYMENT_MODE==insights.

    $ django-admin maintain-pe-group
    """

    help = "Creates/updates partner engineering group with permissions"

    def handle(self, *args, **options):
        pe_group, group_created = Group.objects.get_or_create(name=PE_GROUP_NAME)
        if group_created:
            self.stdout.write(f"Created group '{PE_GROUP_NAME}'")
        else:
            self.stdout.write(f"Group '{PE_GROUP_NAME}' already exists")

        pe_role, role_created = Role.objects.get_or_create(name=PE_ROLE_NAME)
        if role_created:
            self.stdout.write(f"Created role '{PE_ROLE_NAME}'")
        else:
            self.stdout.write(f"Role '{PE_ROLE_NAME}' already exists")

        pe_perms = [
            # groups
            ("galaxy", "view_group"),
            ("galaxy", "delete_group"),
            ("galaxy", "add_group"),
            ("galaxy", "change_group"),
            # users
            ("galaxy", "view_user"),
            ("galaxy", "delete_user"),
            ("galaxy", "add_user"),
            ("galaxy", "change_user"),
            # collections
            ("ansible", "modify_ansible_repo_content"),
            ("ansible", "delete_collection"),
            # namespaces
            ("galaxy", "add_namespace"),
            ("galaxy", "change_namespace"),
            ("galaxy", "upload_to_namespace"),
            ("galaxy", "delete_namespace"),
        ]
        for app_label, codename in pe_perms:
            perm = Permission.objects.filter(
                content_type__app_label=app_label,
                codename=codename,
            ).first()
            if perm:
                pe_role.permissions.add(perm)
            else:
                self.stdout.write(f"Permission {app_label}.{codename} not found.")

        assign_role(pe_role, pe_group, self)

        self.stdout.write(
            f"Permissions assigned to '{PE_ROLE_NAME}', Role assigned to '{PE_GROUP_NAME}'"
        )
