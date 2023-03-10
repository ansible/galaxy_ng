from django.db import connection

from insights_analytics_collector import Collector as BaseCollector
from rest_framework.fields import DateTimeField


class Collector(BaseCollector):

    def __init__(self, collection_type, collector_module, logger):
        super().__init__(collection_type=collection_type,
                         collector_module=collector_module,
                         logger=logger)

    @staticmethod
    def db_connection():
        return connection


    def get_last_gathering(self):
        return self._last_gathering()

    def _is_shipping_configured(self):
#         if not settings.PINAKES_INSIGHTS_TRACKING_STATE:
#             self.logger.warning(
#                 "Insights for Automation Service Catalog is not enabled."
#             )
#             return False

#         if not settings.PINAKES_INSIGHTS_URL:
#             self.logger.error("PINAKES_INSIGHTS_URL is not set")
#             return False

#         if not settings.PINAKES_INSIGHTS_AUTH_METHOD:
#             self.logger.error("PINAKES_INSIGHTS_AUTH_METHOD is not set")
#             return False

#         if settings.PINAKES_INSIGHTS_AUTH_METHOD == "credential":
#             if (
#                 settings.PINAKES_INSIGHTS_USERNAME == "unknown"
#                 or settings.PINAKES_INSIGHTS_PASSWORD == "unknown"
#             ):
#                 self.logger.error(
#                     "PINAKES_INSIGHTS_USERNAME and PINAKES_INSIGHTS_PASSWORD \
# are not set"
#                 )
#                 return False

        return True

    def _is_valid_license(self):
        # TODO: need license information and validation logics
        return True

    def _last_gathering(self):
        # job = get_current_job()
        # last_gather = job.meta.get("last_gather", None) if job else None
        last_gather = None

        return (
            DateTimeField().to_internal_value(last_gather)
            if last_gather
            else None
        )

    def _load_last_gathered_entries(self):
        # job = get_current_job()

        # last_entries = job.meta.get("last_gathered_entries", {}) if job else {}
        last_entries = {}
        for key, value in last_entries.items():
            last_entries[key] = DateTimeField().to_internal_value(value)

        return last_entries

    def _save_last_gathered_entries(self, last_gathered_entries):
        self.logger.info(f"Save last_entries: {last_gathered_entries}")

        # job = get_current_job()
        # if job:
        #     job.meta["last_gathered_entries"] = last_gathered_entries
        #     job.save_meta()

    def _save_last_gather(self):
        self.logger.info(f"Save last_gather: {self.gather_until}")

        # job = get_current_job()
        # if job:
        #     job.meta["last_gather"] = self.gather_until.strftime(
        #         "%Y-%m-%dT%H:%M:%S.%fZ"
        #     )
        #     job.save_meta()