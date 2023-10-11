import logging

from django.core.management.base import BaseCommand
from galaxy_ng.app.metrics_collection.lightspeed.collector import Collector
from galaxy_ng.app.metrics_collection.lightspeed import data as lightspeed_data
from django.utils.timezone import now, timedelta

logger = logging.getLogger("metrics_collection.export_lightspeed")


class Command(BaseCommand):
    """Django management command to export collections data to s3 bucket"""

    def handle(self, *args, **options):
        """Handle command"""

        collector = Collector(
            collector_module=lightspeed_data,
            collection_type=Collector.MANUAL_COLLECTION,
            logger=logger,
        )

        collector.gather(since=now() - timedelta(days=8), until=now() - timedelta(days=1))

        self.stdout.write("Gather Analytics => S3(Lightspeed): Completed ")


if __name__ == "__main__":
    cmd = Command()
    cmd.handle()
