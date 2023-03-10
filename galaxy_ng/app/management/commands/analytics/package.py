import insights_analytics_collector as base

from django.conf import settings


class Package(base.Package):
    CERT_PATH = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
    PAYLOAD_CONTENT_TYPE = "application/vnd.redhat.tower.tower_payload+tgz"

    def _tarname_base(self):
        timestamp = self.collector.gather_until
        return f'{settings.SYSTEM_UUID}-{timestamp.strftime("%Y-%m-%d-%H%M%S%z")}'

    def get_ingress_url(self):
        return getattr(settings, 'AUTOMATION_ANALYTICS_URL', None)

    def _get_rh_user(self):
        return getattr(settings, 'REDHAT_USERNAME', None)

    def _get_rh_password(self):
        return getattr(settings, 'REDHAT_PASSWORD', None)


    def shipping_auth_mode(self):
        return self.SHIPPING_AUTH_USERPASS