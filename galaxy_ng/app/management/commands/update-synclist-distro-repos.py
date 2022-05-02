import logging

from django.core.management.base import BaseCommand
from django.db import transaction

from galaxy_ng.app.models import SyncList

log = logging.getLogger(__name__)


class Command(BaseCommand):
    """This command modifies SyncLists repository to point to upstream_repository

    Example:

    django-admin update-synclist-distro-repos --point-each-to-upstream
    django-admin update-synclist-distro-repos --point-each-to-synclist-repo
    """

    def add_arguments(self, parser):
        parser.add_argument("--point-each-to-upstream",
                            action="store_true",
                            help="Update every SyncList's repository to point to the upstream repository (published, by default)",
                            default=False,
                            required=False,
                            )
        parser.add_argument("--point-each-to-synclist-repo",
                            action="store_true",
                            help="Update every SyncList's repository to point to the per group synclist ('12345-synclist' for example)",
                            default=False,
                            required=False,
                            )

    def handle(self, *args, **options):
        log.debug('options: %s', repr(options))

        synclists = SyncList.objects.all()

        if options["point_each_to_upstream"]:
            log.debug("Updating all synclists.repository to point to upstream_repository")

            with transaction.atomic():
                for synclist in synclists:
                    log.debug('repo: %s upstream: %s', synclist.repository, synclist.upstream_repository)
                    synclist.repository = synclist.upstream_repository
                    synclist.save()

        if options["point_each_to_synclist_repo"]:
            log.debug("Updating all synclists.repository to point to synclist repo")
            with transaction.atomic():
                for synclist in synclists:
                    log.debug('repo: %s upstream: %s', synclist.repository, synclist.upstream_repository)
                    # TODO: figure out what the synclist repo is, and if it should exist
                    #       ie, .collections or .namespaces is not empty
                    # synclist.repository = synclist.upstream_repository
                    # synclist.save()
