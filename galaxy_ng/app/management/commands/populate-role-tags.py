from gettext import gettext as _
import uuid

import django_guid
from django.core.management.base import BaseCommand

from galaxy_ng.app.api.v1.models import LegacyRole, LegacyRoleTag


class Command(BaseCommand):
    """
    Django management command for populating role tags ('_ui/v1/tags/roles/') within the system.
    This command is run nightly on galaxy.ansible.com.
    """

    help = _("Populate the 'LegacyRoleTag' model with tags from LegacyRole 'full_metadata__tags'.")

    def handle(self, *args, **options):
        # Set logging correlation ID for this management command
        # (not auto-generated like in HTTP requests)
        django_guid.set_guid(str(uuid.uuid4()))
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
