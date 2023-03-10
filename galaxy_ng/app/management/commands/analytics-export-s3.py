import logging

from django.core.management.base import BaseCommand
from galaxy_ng.app.management.commands.analytics.collector import Collector
from galaxy_ng.app.management.commands.analytics import galaxy_collector
from django.utils.timezone import now, timedelta

logger = logging.getLogger("analytics")


class Command(BaseCommand):
    """Django management command to export collections data to s3 bucket"""

    def handle(self, *args, **options):
        """Handle command"""

        collector = Collector(
            collector_module=galaxy_collector,
            collection_type="manual",
            logger=logger,
        )

        collector.gather(since=now() - timedelta(days=8), until=now() - timedelta(days=1))

        print("Completed ")


if __name__ == "__main__":
    cmd = Command()
    cmd.handle()
