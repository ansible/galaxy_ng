import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """This command updates all AnsibleDistribution in the format of #####-synclists
    to point to the published repo.

    Example:
    django-admin update-synclist-distros
    """

    def handle(self, *args, **options):
        log.info(
            "Updating all AnsibleDistribution in the format of #####-synclists "
            "to point to the published repo"
        )

        published_repo = AnsibleRepository.objects.get(name="published")

        with transaction.atomic():
            synclist_distros = AnsibleDistribution.objects.filter(base_path__endswith="-synclist")
            for distro in synclist_distros:
                if not distro.repository or distro.repository.pk != published_repo.pk:
                    distro.repository = published_repo
                    distro.save()
                    log.info("distro edited: %s", distro.name)
