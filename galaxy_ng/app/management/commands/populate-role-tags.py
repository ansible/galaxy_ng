from gettext import gettext as _

import django_guid
from django.core.management.base import BaseCommand

# from galaxy_ng.app.api.v1.tasks import legacy_sync_from_upstream
from galaxy_ng.app.api.v1.models import LegacyRole, LegacyRoleTag


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


class Command(BaseCommand):
    """
    Django management command for populating role tags ('_ui/v1/tags/roles/') within the system.
    This command is run nightly on galaxy.ansible.com.
    """

    help = _("Populate the 'LegacyRoleTag' model with tags from LegacyRole 'full_metadata__tags'.")

    def handle(self, *args, **options):
        created_tags = []
        roles = LegacyRole.objects.all()
        for role in roles:
            for name in role.full_metadata["tags"]:
                tag, created = LegacyRoleTag.objects.get_or_create(name=name)
                tag.legacyrole.add(role)

                if created:
                    created_tags.append(tag)

        self.stdout.write(
            "Successfully populated {} tags "
            "from {} roles.".format(len(created_tags), len(roles))
        )
