#!/usr/bin/env python3


import datetime
import logging
import requests

from django.core.management.base import BaseCommand
from django.db import transaction
from pulp_ansible.app.models import Collection, CollectionDownloadCount


log = logging.getLogger(__name__)


DEFAULT_UPSTREAM = 'https://old-galaxy.ansible.com'

SKIPLIST = [
    'larrymou9',
    'github_qe_test_user',
]


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            '--upstream',
            default=DEFAULT_UPSTREAM,
            help=f"remote host to retrieve data from [{DEFAULT_UPSTREAM}]"
        )
        parser.add_argument('--limit', type=int, help="stop syncing after N collections")
        parser.add_argument(
            '--force', action='store_true', help='sync all counts and ignore last update'
        )

    def handle(self, *args, **options):
        log.info(f"Processing upstream download counts from {options['upstream']}")
        upstream = options['upstream']
        limit = options['limit']

        now = datetime.datetime.now()

        collection_count = 0
        collection_total = Collection.objects.count()
        for collection in Collection.objects.all().order_by('pulp_created'):

            namespace = collection.namespace
            name = collection.name
            collection_count += 1

            log.info(f'{collection_total}|{collection_count} {namespace}.{name}')

            if limit and collection_count > limit:
                break

            if namespace in SKIPLIST:
                continue

            # optimization: don't try to resync something that changed less than a day ago
            counter = CollectionDownloadCount.objects.filter(namespace=namespace, name=name).first()
            if counter is not None and not options['force']:
                delta = (now - counter.pulp_last_updated.replace(tzinfo=None)).total_seconds()
                if (delta / 60) < (24 * 60 * 60):
                    continue

            detail_url = (
                upstream
                + f'/api/internal/ui/repo-or-collection-detail/?namespace={namespace}&name={name}'
            )
            log.info('\t' + detail_url)
            drr = requests.get(detail_url)
            ds = drr.json()
            if 'data' not in ds:
                log.error(ds)
                continue
            if 'collection' not in ds['data']:
                log.error(ds['data'].keys())
                continue

            cid = ds['data']['collection']['id']
            dcount = ds['data']['collection']['download_count']
            log.info(f'\t{cid} {namespace}.{name} downloads:{dcount}')

            if counter is None:
                log.info(f'\tcreate downloadcount for {namespace}.{name} with value of {dcount}')
                with transaction.atomic():
                    counter = CollectionDownloadCount(
                        namespace=namespace,
                        name=name,
                        download_count=dcount
                    )
                    counter.save()
                continue

            if counter.download_count < dcount:
                log.info(
                    f'\tupdate downloadcount for {namespace}.{name}'
                    + f' from {counter.download_count} to {dcount}'
                )
                with transaction.atomic():
                    counter.download_count = dcount
                    continue
