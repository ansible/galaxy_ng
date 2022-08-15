from django.core.management import BaseCommand

from pulpcore.plugin.util import assign_role

from galaxy_ng.app.models.auth import Group

PE_GROUP_NAME = "system:partner-engineers"


class Command(BaseCommand):
    """
    This command creates or updates a partner engineering group
    with a standard set of permissions via Galaxy locked roles.
    Intended to be used for settings.GALAXY_DEPLOYMENT_MODE==insights.

    $ django-admin maintain-pe-group
    """

    help = "Creates/updates partner engineering group with permissions"

    def handle(self, *args, **options):
        pe_group, group_created = Group.objects.get_or_create(name=PE_GROUP_NAME)
        if group_created:
            self.stdout.write(f"Created group '{PE_GROUP_NAME}'")
        else:
            self.stdout.write(f"Group '{PE_GROUP_NAME}' already exists")

        pe_roles = [
            'galaxy.group_admin',
            'galaxy.user_admin',
            'galaxy.collection_admin',
        ]

        roles_in_group = [group_role.role.name for group_role in pe_group.object_roles.all()]
        for role in pe_roles:
            if role not in roles_in_group:
                assign_role(rolename=role, entity=pe_group)

        self.stdout.write(
            f"Roles assigned to '{PE_GROUP_NAME}'"
        )
