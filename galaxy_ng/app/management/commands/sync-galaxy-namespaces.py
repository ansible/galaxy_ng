import django_guid
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from galaxy_ng.app.utils.galaxy import upstream_namespace_iterator
from galaxy_ng.app.utils.galaxy import find_namespace
from galaxy_ng.app.utils.legacy import process_namespace


# Set logging_uid, this does not seem to get generated when task called via management command
django_guid.set_guid(django_guid.utils.generate_guid())


User = get_user_model()


class Command(BaseCommand):
    """
    Iterates through every upstream namespace and syncs it.
    """

    help = 'Sync upstream namespaces+owners from [old-]galaxy.ansible.com'

    def add_arguments(self, parser):
        parser.add_argument("--baseurl", default="https://old-galaxy.ansible.com")
        parser.add_argument("--name", help="find and sync only this namespace name")
        parser.add_argument("--id", help="find and sync only this namespace id")
        parser.add_argument("--force", action="store_true")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--start_page", type=int)

    def echo(self, message, style=None):
        style = style or self.style.SUCCESS
        self.stdout.write(style(message))

    def handle(self, *args, **options):

        if options.get('name'):
            ns_name, ns_info = find_namespace(baseurl=options['baseurl'], name=options['name'])
            self.echo(f'PROCESSING {ns_info["id"]}:{ns_name}')
            process_namespace(ns_name, ns_info, force=options['force'])

        elif options.get('id'):
            ns_name, ns_info = find_namespace(baseurl=options['baseurl'], id=options['id'])
            self.echo(f'PROCESSING {ns_info["id"]}:{ns_name}')
            process_namespace(ns_name, ns_info, force=options['force'])

        else:

            count = 0
            for total, namespace_info in upstream_namespace_iterator(
                baseurl=options['baseurl'],
                start_page=options['start_page'],
                limit=options['limit'],
            ):

                count += 1
                namespace_name = namespace_info['name']

                self.echo(
                    f'({total}|{count})'
                    + f' PROCESSING {namespace_info["id"]}:{namespace_name}'
                )
                process_namespace(namespace_name, namespace_info, force=options['force'])
