import logging

from django.core.management.base import BaseCommand
from galaxy_ng.app.management.commands.analytics.collector import Collector
from galaxy_ng.app.management.commands.analytics import galaxy_collector
from django.utils.timezone import now, timedelta

import sys

logger = logging.getLogger("analytics")

class Command(BaseCommand):
    """Django management command to export collections data to s3 bucket
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "--start-date",
            help="date range start",
            type=str,
            default="start_date",
            required=False
        )
        parser.add_argument(
            "--end-date",
            help="date range end",
            type=str,
            default="end_date",
            required=False
        )
        parser.add_argument(
            "--s3-buckett",
            help="Name of the bucket",
            required=False,
            type=str,
        )
        parser.add_argument(
            "--username",
            help="s3 username",
            required=False,
            type=str,
        )
        parser.add_argument(
            "--password",
            help="s3 password",
            required=False,
            type=str,
        )

    def handle(self, *args, **options):
        """Handle command"""

        collector = Collector(
            collector_module=galaxy_collector,
            collection_type="dry-run",
            logger=logger,
        )
        
        start = now() - timedelta(days=1)
        end = now() - timedelta(days=1)
        print(collector.gather(since=start, until=end))

if __name__ == "__main__":
    cmd = Command()
    cmd.handle()