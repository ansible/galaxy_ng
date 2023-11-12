from contextlib import suppress
from django.core.management.base import BaseCommand
from galaxy_ng.app.models.config import Setting
from django.conf import settings
from dynaconf.utils import upperfy
from galaxy_ng.app.dynamic_settings import DYNAMIC_SETTINGS_SCHEMA


class Command(BaseCommand):
    """This command sets, read, delete Galaxy Setting.

    Examples:
    django-admin galaxy-settings set --key=foo --value=bar
    django-admin galaxy-settings set --key=foo --value=bar --is-secret

    django-admin galaxy-settings get --key=foo
    django-admin galaxy-settings get --key=foo --raw

    django-admin galaxy-settings delete --key=foo --all-versions
    django-admin galaxy-settings delete --all

    django-admin galaxy-settings list
    django-admin galaxy-settings list --raw

    django-admin galaxy-settings inspect --key=foo

    django-admin galaxy-settings update_cache
    django-admin galaxy-settings clean_cache

    django-admin galaxy-settings allowed_keys
    """

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='subcommand', required=True)

        # Subcommand: set
        set_parser = subparsers.add_parser('set', help='Set a Galaxy setting')
        set_parser.add_argument('--key', required=True, help='Setting key')
        set_parser.add_argument('--value', required=True, help='Setting value')
        set_parser.add_argument('--is-secret', action='store_true', help='Mark as secret')

        # Subcommand: get
        get_parser = subparsers.add_parser('get', help='Get a Galaxy setting')
        get_parser.add_argument('--key', required=True, help='Setting key')
        get_parser.add_argument('--raw', action='store_true', help='Raw value from DB')
        get_parser.add_argument('--default', help='Default value')

        # Subcommand: delete
        delete_parser = subparsers.add_parser('delete', help='Delete a Galaxy setting')
        delete_parser.add_argument('--key', help='Setting key')
        delete_parser.add_argument(
            '--all-versions', action='store_true', help='Delete all versions'
        )
        delete_parser.add_argument('--all', action='store_true', help='Delete all settings')

        # Subcommand: list
        list_parser = subparsers.add_parser('list', help='List Galaxy settings')
        list_parser.add_argument('--raw', action='store_true', help='Raw value from DB')

        # Subcommand: inspect
        inspect_parser = subparsers.add_parser('inspect', help='Inspect a Galaxy setting')
        inspect_parser.add_argument('--key', required=True, help='Setting key')

        # Subcommand: update_cache
        subparsers.add_parser('update_cache', help='Update settings cache')

        # Subcommand: clean_cache
        subparsers.add_parser('clean_cache', help='Clean settings cache')

        # Subcommand: allowed_keys
        subparsers.add_parser('allowed_keys', help='List allowed settings keys')

    def echo(self, message):
        self.stdout.write(self.style.SUCCESS(str(message)))

    def handle(self, *args, **options):
        subcommand = options['subcommand']
        result = getattr(self, f'handle_{subcommand}')(*args, **options)
        self.echo(result)

    def handle_set(self, *args, **options):
        key = options['key']
        value = options['value']
        is_secret = options['is_secret']
        return Setting.set_value_in_db(key, value, is_secret=is_secret)

    def handle_get(self, *args, **options):
        key = options['key']
        raw = options['raw']
        default = options['default']
        if raw:
            try:
                return Setting.get_value_from_db(upperfy(key))
            except Setting.DoesNotExist:
                return default
        return Setting.get(upperfy(key), default=default)

    def handle_delete(self, *args, **options):
        key = options['key']
        all_versions = options['all_versions']
        all_settings = options['all']
        if all_settings:
            result = Setting.objects.all().delete()
            Setting.update_cache()
            return result

        with suppress(Setting.DoesNotExist):
            if key and all_versions:
                return Setting.delete_all_versions(upperfy(key))
            if key:
                return Setting.delete_latest_version(upperfy(key))

        return "Nothing to delete"

    def handle_list(self, *args, **options):
        raw = options['raw']
        data = Setting.as_dict()
        if raw:
            return data
        return {k: Setting.get(k) for k in data}

    def handle_inspect(self, *args, **options):
        key = options['key']
        from dynaconf.utils.inspect import get_history
        return get_history(settings, key)

    def handle_update_cache(self, *args, **options):
        return Setting.update_cache()

    def handle_clean_cache(self, *args, **options):
        return Setting.clean_cache()

    def handle_allowed_keys(self, *args, **options):
        return DYNAMIC_SETTINGS_SCHEMA.keys()
