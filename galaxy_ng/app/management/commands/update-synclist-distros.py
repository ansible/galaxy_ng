import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """This command modifies AnsibleDistributions in format of #####-synclists
    to change which repository they point to.

    Example:

    django-admin update-synclist-distros --point-each-to-default-repo
    django-admin update-synclist-distros --point-each-to-synclist-repo
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--point-each-to-default-repo",
            action="store_true",
            help="Update all AnsibleDistribution in format of #####-synclists "
            "to point to published repo",
            default=False,
            required=False,
        )
        parser.add_argument(
            "--point-each-to-synclist-repo",
            action="store_true",
            help="Update all AnsibleDistribution in format of #####-synclists "
            "to point to repo of the same name ('12345-synclist' for example)",
            default=False,
            required=False,
        )

    def handle(self, *args, **options):
        log.debug("options: %s", repr(options))

        if options["point_each_to_default_repo"]:
            log.info(
                "Updating all AnsibleDistribution in format of #####-synclists "
                "to point to published repo"
            )

            published_repo = AnsibleRepository.objects.get(name="published")

            with transaction.atomic():
                synclist_distros = AnsibleDistribution.objects.filter(
                    base_path__endswith="-synclist"
                )
                for distro in synclist_distros:
                    log.debug("distro: %s", distro)
                    distro.repository = published_repo
                    distro.save()

        if options["point_each_to_synclist_repo"]:
            log.info(
                "Updating all AnsibleDistribution in format of #####-synclists "
                "to point to repo of the same name"
            )

            with transaction.atomic():
                synclist_distros = AnsibleDistribution.objects.filter(
                    base_path__endswith="-synclist"
                )
                for distro in synclist_distros:
                    log.debug("distro: %s", distro)
                    synclist_repo, _ = AnsibleRepository.objects.get_or_create(
                        name=distro.base_path
                    )
                    distro.repository = synclist_repo
                    distro.save()
