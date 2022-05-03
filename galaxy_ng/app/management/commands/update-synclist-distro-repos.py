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

                    if not synclist.collections.all() and not synclist.namespaces.all():
                        # If nothing is specified to customize the synclist, we don't need a synclist repo
                        log.debug('This synclist does not specify any excludes, so no need to create a synclist repo')
                        continue

                    log.debug('This synclist has exclude collections or namespaces, so it needs to point to correct synclist repo')
                    # look up repo based on synclist.name
                    synclist_repo = AnsibleRepository.get(name=synclist.name)

                    log.debug('Pointing synclist %s to synclist repo %s', synclist, synclist_repo)
                    synclist.repository = synclist_repo
                    synclist.save()
