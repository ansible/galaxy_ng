import base64
import json
from django.conf import settings

from insights_analytics_collector import Package as InsightsAnalyticsPackage


class Package(InsightsAnalyticsPackage):
    CERT_PATH = "/etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem"
    PAYLOAD_CONTENT_TYPE = "application/vnd.redhat.automation-hub.hub_payload+tgz"

    def _tarname_base(self):
        timestamp = self.collector.gather_until
        return f'galaxy-hub-analytics-{timestamp.strftime("%Y-%m-%d-%H%M")}'

    def get_ingress_url(self):
        return settings.GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL

    def _get_rh_user(self):
        return settings.GALAXY_METRICS_COLLECTION_REDHAT_USERNAME

    def _get_rh_password(self):
        return settings.GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD

    def _get_x_rh_identity(self):
        """Auth: x-rh-identity header for HTTP POST request to cloud
        Optional, if shipping_auth_mode() redefined to SHIPPING_AUTH_IDENTITY
        """
        tenant_id = f"{int(settings.GALAXY_METRICS_COLLECTION_ORG_ID):07d}"
        identity = {
            "identity": {
                "type": "User",
                "account_number": tenant_id,
                "user": {"is_org_admin": True},
                "internal": {"org_id": tenant_id}
            }
        }
        identity = base64.b64encode(json.dumps(identity).encode("utf8"))
        return identity

    def hub_version(self):
        try:
            config_data = self.collector.collections.get("config", {}).data or {}
            parsed = json.loads(config_data)
            return parsed.get('hub_version', '0.0')
        except json.decoder.JSONDecodeError:
            return "unknown version"

    def _get_http_request_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'GalaxyNG | Red Hat Ansible Automation Platform ({self.hub_version()})'
        }
        return headers

    def shipping_auth_mode(self):
        return settings.GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE
