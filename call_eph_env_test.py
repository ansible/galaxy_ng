"""
Call get_client against ephemeral env

export NAMESPACE="ephemeral-akifeh"
export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/api/automation-hub/"
export HUB_AUTH_URL="https://mocks-keycloak-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/auth/realms/redhat-external/protocol/openid-connect/token"
"""

from galaxy_ng.tests.integration.conftest import AnsibleConfigFixture
from galaxy_ng.tests.integration.utils import get_client

config = AnsibleConfigFixture("ansible_partner")
api_client = get_client(config)

print(config.get("auth_url"))
# print(config.get("token"))
print(config.get("username"))
# print(api_client)
response = api_client('/api/automation-hub/')
print(response)
# api_client("http://www.google.com")
