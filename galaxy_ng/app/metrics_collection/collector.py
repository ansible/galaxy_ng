from django.db import connection
from insights_analytics_collector import Collector as BaseCollector


class Collector(BaseCollector):
    def _is_valid_license(self):
        return True

    @staticmethod
    def db_connection():
        return connection
