import logging
import yaml
import sys
import time

import django_guid
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from galaxy_ng.app.utils.galaxy import upstream_collection_iterator
from galaxy_ng.app.utils.legacy import process_namespace

from pulp_ansible.app.models import CollectionVersion
from pulp_ansible.app.models import CollectionRemote
from pulp_ansible.app.models import AnsibleRepository
from pulp_ansible.app.tasks.collections import sync
from pulp_ansible.app.tasks.collections import rebuild_repository_collection_versions_metadata

from pulpcore.plugin.tasking import dispatch
from pulpcore.plugin.constants import TASK_FINAL_STATES, TASK_STATES


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


logger = logging.getLogger(__name__)


User = get_user_model()


class Command(BaseCommand):
    """
    Iterates through every upstream namespace and syncs it.
    """

    help = 'Sync upstream namespaces+owners from [old-]galaxy.ansible.com'

    def add_arguments(self, parser):
        parser.add_argument("--baseurl", default="https://old-galaxy.ansible.com")
        parser.add_argument("--namespace", help="find and sync only this namespace name")
        parser.add_argument("--name", help="find and sync only this name")
        parser.add_argument("--remote", help="name for the remote", default="published")
        parser.add_argument("--repository", help="name for the repository", default="published")
        parser.add_argument("--rebuild_only", action="store_true", help="only rebuild metadata")
        parser.add_argument("--limit", type=int)

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        logger.info(style(message))

    def handle(self, *args, **options):

        remote = CollectionRemote.objects.filter(name=options['remote']).first()
        if not remote:
            raise Exception('could not find remote')
        repo = AnsibleRepository.objects.filter(name=options['repository']).first()
        if not repo:
            raise Exception('could not find repo')

        counter = 0
        processed_namespaces = set()
        for namespace_info, collection_info, collection_versions in upstream_collection_iterator(
            baseurl=options['baseurl'],
            collection_namespace=options['namespace'],
            collection_name=options['name'],
            limit=options['limit'],
        ):
            counter += 1
            logger.info(
                f"{counter}. {collection_info['namespace']['name']}.{collection_info['name']}"
                + f" versions:{len(collection_versions)}"
            )

            if namespace_info['name'] not in processed_namespaces:
                process_namespace(namespace_info['name'], namespace_info)
                processed_namespaces.add(namespace_info['name'])

            # pulp_ansible sync isn't smart enough to do this ...
            should_sync = False
            should_rebuild = False
            for cvdata in collection_versions:
                cv = CollectionVersion.objects.filter(
                    namespace=collection_info['namespace']['name'],
                    name=collection_info['name'],
                    version=cvdata['version']
                ).first()

                if not cv:
                    should_sync = True
                    should_rebuild = True
                elif not cv.contents or not cv.requires_ansible:
                    should_rebuild = True

            self.echo(f'sync: {should_sync}')
            self.echo(f'rebuild: {should_rebuild}')

            if should_sync and not options['rebuild_only']:

                # build a single collection requirements
                requirements = {
                    'collections': [
                        collection_info['namespace']['name'] + '.' + collection_info['name']
                    ]
                }
                requirements_yaml = yaml.dump(requirements)

                # set the remote's requirements
                remote.requirements_file = requirements_yaml
                remote.save()

                self.echo(
                    f"dispatching sync for {collection_info['namespace']['name']}"
                    + f".{collection_info['name']}"
                )
                self.do_sync_dispatch(
                    remote,
                    repo,
                    collection_info['namespace']['name'],
                    collection_info['name']
                )

            if should_rebuild:
                self.echo(
                    f"dispatching rebuild for {collection_info['namespace']['name']}"
                    + f".{collection_info['name']}"
                )
                self.do_rebuild_dispatch(
                    repo,
                    collection_info['namespace']['name'],
                    collection_info['name']
                )

    def do_sync_dispatch(self, remote, repository, namespace, name):

        # dispatch the real pulp_ansible sync code
        task = dispatch(
            sync,
            kwargs={
                'remote_pk': str(remote.pk),
                'repository_pk': str(repository.pk),
                'mirror': False,
                'optimize': False,
            },
            exclusive_resources=[repository],
        )

        while task.state not in TASK_FINAL_STATES:
            time.sleep(2)
            self.echo(f"Syncing {namespace}.{name} {task.state}")
            task.refresh_from_db()

        self.echo(f"Syncing {namespace}.{name} {task.state}")

        if task.state == TASK_STATES.FAILED:
            self.echo(
                f"Task failed with error ({namespace}.{name}): {task.error}", self.style.ERROR
            )
            sys.exit(1)

    def do_rebuild_dispatch(self, repository, namespace, name):

        repository_version = repository.latest_version()

        task = dispatch(
            rebuild_repository_collection_versions_metadata,
            kwargs={
                'repository_version_pk': str(repository_version.pk),
                'namespace': namespace,
                'name': name
            },
            exclusive_resources=[repository],
        )

        while task.state not in TASK_FINAL_STATES:
            time.sleep(2)
            self.echo(f"Rebuild {namespace}.{name} {task.state}")
            task.refresh_from_db()

        self.echo(f"Rebuild {namespace}.{name} {task.state}")

        if task.state == TASK_STATES.FAILED:
            self.echo(
                f"Task failed with error ({namespace}.{name}): {task.error}", self.style.ERROR
            )
            sys.exit(1)
