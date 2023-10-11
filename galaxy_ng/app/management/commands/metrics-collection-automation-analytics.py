import logging

from django.core.management.base import BaseCommand
from galaxy_ng.app.metrics_collection.automation_analytics.collector import Collector
from galaxy_ng.app.metrics_collection.automation_analytics import data as automation_analytics_data

logger = logging.getLogger("metrics_collection.export_automation_analytics")


class Command(BaseCommand):
    help = ("Django management command to export collections data to "
            "ingress -> automation metrics_collection")

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', dest='dry-run', action='store_true',
            help='Gather metrics_collection without shipping'
        )
        parser.add_argument(
            '--ship', dest='ship', action='store_true',
            help='Enable to ship metrics to the Red Hat Cloud'
        )

    def handle(self, *args, **options):
        """Handle command"""

        opt_ship = options.get('ship')
        opt_dry_run = options.get('dry-run')

        if opt_ship and opt_dry_run:
            self.logger.error('Both --ship and --dry-run cannot be processed at the same time.')
            return

        collector = Collector(
            collector_module=automation_analytics_data,
            collection_type=Collector.MANUAL_COLLECTION if opt_ship else Collector.DRY_RUN,
            logger=logger
        )

        tgzfiles = collector.gather()
        if tgzfiles:
            for tgz in tgzfiles:
                self.stdout.write(tgz)
        else:
            self.stdout.write("No metrics_collection tarballs collected")
