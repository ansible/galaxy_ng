from django.conf import settings
from galaxy_ng.app.metrics_collection.collector import Collector as BaseCollector
from galaxy_ng.app.metrics_collection.lightspeed.package import Package


class Collector(BaseCollector):
    def __init__(self, collection_type, collector_module, logger):
        super().__init__(
            collection_type=collection_type, collector_module=collector_module, logger=logger
        )

    @staticmethod
    def _package_class():
        return Package

    def is_enabled(self):
        if not settings.GALAXY_METRICS_COLLECTION_LIGHTSPEED_ENABLED:
            self.logger.log(self.log_level,
                            "Metrics Collection for Ansible Lightspeed not enabled.")
            return False
        return super().is_enabled()

    def get_last_gathering(self):
        return self._last_gathering()

    def _is_shipping_configured(self):
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
