from django.core.management import BaseCommand
from guardian.shortcuts import assign_perm

from galaxy_ng.app.models.auth import Group

PE_GROUP_NAME = "system:partner-engineers"


class Command(BaseCommand):
    """
    This command creates or updates a partner engineering group
    with a standard set of permissions. Intended to be used for
    settings.GALAXY_DEPLOYMENT_MODE==insights.

    $ django-admin maintain-pe-group
    """

    help = "Creates/updates partner engineering group with permissions"

    def handle(self, *args, **options):
        pe_group, created = Group.objects.get_or_create(name=PE_GROUP_NAME)
        if created:
            self.stdout.write(f"Created group '{PE_GROUP_NAME}'")
        else:
            self.stdout.write(f"Group '{PE_GROUP_NAME}' already exists")

        pe_perms = [
            # groups
            "galaxy.view_group",
            "galaxy.delete_group",
            "galaxy.add_group",
            "galaxy.change_group",
            # users
            "galaxy.view_user",
            "galaxy.delete_user",
            "galaxy.add_user",
            "galaxy.change_user",
            # collections
            "ansible.modify_ansible_repo_content",
            "ansible.delete_collection",
            # namespaces
            "galaxy.add_namespace",
            "galaxy.change_namespace",
            "galaxy.upload_to_namespace",
            "galaxy.delete_namespace",
        ]

        for perm in pe_perms:
            assign_perm(perm, pe_group)

        self.stdout.write(f"Permissions assigned to '{PE_GROUP_NAME}'")
