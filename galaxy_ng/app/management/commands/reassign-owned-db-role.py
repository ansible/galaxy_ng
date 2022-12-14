from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """This command reassigns database tableowners.

    This is meant for the CRC instance where older tables are owned by `galaxy_ng`,
    and newer tables are owned by `postgres`.

    It will update all database objects owned by old_role (galaxy_ng)
    to be owned by new_role (postgres).

    https://www.postgresql.org/docs/current/sql-reassign-owned.html
    REASSIGN OWNED requires membership on both the source role(s) and the target role.

    """

    def handle(self, *args, **options):

        with connection.cursor() as cursor:
            cursor.execute(
                "REASSIGN OWNED BY galaxy_ng TO postgres;"
        )
