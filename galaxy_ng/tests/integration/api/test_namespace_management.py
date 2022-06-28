"""test_namespace_management.py - Test related to namespaces.

See: https://issues.redhat.com/browse/AAH-1303

"""
import pytest
from ansible.errors import AnsibleError

from ..utils import get_client
from ..utils import generate_unused_namespace
from ..utils import get_all_namespaces

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.namespace
@pytest.mark.parametrize(
    "api_version",
    [
        'v3',
        '_ui/v1'
    ]
)
def test_namespace_create_and_delete(ansible_config, api_version):
    """Tests whether a namespace can be created and deleted"""

    # http://192.168.1.119:8002/api/automation-hub/_ui/v1/namespaces/
    # http://192.168.1.119:8002/api/automation-hub/v3/namespaces/
    # {name: "testnamespace1", groups: []}

    config = ansible_config("partner_engineer")
    api_client = get_client(config, request_token=True, require_auth=True)

    new_namespace = generate_unused_namespace(api_client=api_client, api_version=api_version)
    payload = {'name': new_namespace, 'groups': []}
    resp = api_client(f'/api/automation-hub/{api_version}/namespaces/', args=payload, method='POST')
    assert resp['name'] == new_namespace

    existing2 = get_all_namespaces(api_client=api_client, api_version=api_version)
    existing2 = dict((x['name'], x) for x in existing2)
    assert new_namespace in existing2

    # This should throw an AnsibleError because the response body is an
    # empty string and can not be parsed to JSON
    try:
        resp = api_client(
            f'/api/automation-hub/{api_version}/namespaces/{new_namespace}/',
            method='DELETE'
        )
    except AnsibleError:
        pass

    existing3 = get_all_namespaces(api_client=api_client, api_version=api_version)
    existing3 = dict((x['name'], x) for x in existing3)
    assert new_namespace not in existing3
