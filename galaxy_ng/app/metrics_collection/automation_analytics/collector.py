from django.conf import settings

from galaxy_ng.app.metrics_collection.collector import Collector as BaseCollector
from galaxy_ng.app.metrics_collection.automation_analytics.package import Package


class Collector(BaseCollector):
    @staticmethod
    def _package_class():
        return Package

    def is_enabled(self):
        if not settings.GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_ENABLED:
            self.logger.log(self.log_level,
                            "Metrics Collection for Ansible Automation Platform not enabled.")
            return False
        return super().is_enabled()

    def _is_shipping_configured(self):
        auth_valid = bool(settings.GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL)

        # There are two possible types of authentication
        # 1) RH account - user/password
        # 2) X-RH-Identity header (inside cloud or testing)
        if auth_valid:
            auth_valid = settings.GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE in [
                Package.SHIPPING_AUTH_USERPASS,
                Package.SHIPPING_AUTH_IDENTITY]
        if auth_valid:
            if settings.GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE == \
                    Package.SHIPPING_AUTH_USERPASS:
                auth_valid = bool(settings.GALAXY_METRICS_COLLECTION_REDHAT_USERNAME) and \
                    bool(settings.GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD)

            if settings.GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE == \
                    Package.SHIPPING_AUTH_IDENTITY:
                auth_valid = bool(settings.GALAXY_METRICS_COLLECTION_ORG_ID)
        if not auth_valid:
            self.logger.log(self.log_level, "No metrics collection, configuration is invalid. "
                                            "Use --dry-run to gather locally without sending.")
        return auth_valid

    def _last_gathering(self):
        # TODO: Waiting for persistent DB storage in Hub
        # https://issues.redhat.com/browse/AAH-2009
        # return settings.AUTOMATION_ANALYTICS_LAST_GATHER
        return None

    def _load_last_gathered_entries(self):
        # TODO: Waiting for persistent DB storage in Hub
        # https://issues.redhat.com/browse/AAH-2009
        # from awx.conf.models import Setting
        #
        # last_entries = Setting.objects.filter(key='AUTOMATION_ANALYTICS_LAST_ENTRIES').first()
        # last_gathered_entries = \
        #   json.loads((last_entries.value if last_entries is not None else '') or '{}',
        #               object_hook=datetime_hook)
        last_gathered_entries = {}
        return last_gathered_entries

    def _save_last_gathered_entries(self, last_gathered_entries):
        # TODO: Waiting for persistent DB storage in Hub
        # https://issues.redhat.com/browse/AAH-2009
        pass

    def _save_last_gather(self):
        # TODO: Waiting for persistent DB storage in Hub
        # https://issues.redhat.com/browse/AAH-2009
        pass
