import logging
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from galaxy_ng.app.utils.rbac import get_owned_v3_namespaces
from galaxy_ng.app.utils.rbac import add_user_to_v3_namespace
from galaxy_ng.app.utils.rbac import get_v3_namespace_owners


logger = logging.getLogger(__name__)


User = get_user_model()


class Command(BaseCommand):
    """
    Mirror ownership from one user to another
    """

    help = 'Add user <dst_username> as an owner to all the things <src_username> owns.'

    def add_arguments(self, parser):
        parser.add_argument("src_username")
        parser.add_argument("dst_username")
        parser.add_argument("--create", action="store_true")

    def handle(self, *args, **options):

        src_user = User.objects.filter(username=options['src_username']).first()
        dst_user = User.objects.filter(username=options['dst_username']).first()

        if not src_user:
            raise Exception(
                f'source username {options["src_username"]} was not found in the system'
            )

        if not dst_user:
            if not options['create']:
                raise Exception(
                    f'dest username {options["dst_username"]} was not found in the system'
                )
            dst_user, _ = User.objects.get_or_create(username=options['dst_username'])

        # find all the namespaces owned by the source user ...
        namespaces = get_owned_v3_namespaces(src_user)
        for namespace in namespaces:
            current_owners = get_v3_namespace_owners(namespace)
            if dst_user not in current_owners:
                logger.info(f'add {dst_user} to {namespace}')
                add_user_to_v3_namespace(dst_user, namespace)
            else:
                logger.info(f'{dst_user} alreay owns {namespace}')
