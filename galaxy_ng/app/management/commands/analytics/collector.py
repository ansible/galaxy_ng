from django.db import connection

from insights_analytics_collector import Collector as BaseCollector
from galaxy_ng.app.management.commands.analytics.package import Package


class Collector(BaseCollector):
    def __init__(self, collection_type, collector_module, logger):
        super().__init__(
            collection_type=collection_type, collector_module=collector_module, logger=logger
        )

    @staticmethod
    def db_connection():
        return connection

    @staticmethod
    def _package_class():
        return Package

    def get_last_gathering(self):
        return self._last_gathering()

    def _is_shipping_configured(self):
        # TODO: need shipping configuration
        return True

    def _is_valid_license(self):
        # TODO: need license information and validation logics
        return True

    def _last_gathering(self):
        # doing a full scan database dump
        return None

    def _load_last_gathered_entries(self):
        # doing a full scan database dump
        return {}

    def _save_last_gathered_entries(self, last_gathered_entries):
        # doing a full scan database dump
        pass

    def _save_last_gather(self):
        # doing a full scan database dump
        pass
