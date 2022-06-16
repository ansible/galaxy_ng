"""test_move.py - Tests related to the move api.

See: https://issues.redhat.com/browse/AAH-1268

"""
import time

import pytest
from orionutils.generator import build_collection

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME

from ..constants import USERNAME_PUBLISHER
from ..utils import get_client, set_certification, wait_for_task

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.certification
@pytest.mark.collection_move
@pytest.mark.move
def test_move_collection_version(ansible_config, upload_artifact):
    """Tests whether a colleciton can be moved from repo to repo"""

    config = ansible_config("ansible_partner")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    def get_all_collections():
        collections = {
            'staging': {},
            'published': {}
        }
        for repo in collections.keys():
            next_page = f'/api/automation-hub/_ui/v1/collection-versions/?repository={repo}'
            while next_page:
                resp = api_client(next_page)
                for _collection in resp['data']:
                    key = (_collection['namespace'], _collection['name'], _collection['version'])
                    collections[repo][key] = _collection
                next_page = resp.get('links', {}).get('next')
        return collections

    pre = get_all_collections()
    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["tools"],
        }
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)
    assert ckey not in pre['staging']
    assert ckey not in pre['published']

    # import and wait ...
    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)
    assert resp['state'] == 'completed'

    # wait for move task from `inbound-<namespace>` repo to `staging` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

    # Make sure it ended up in staging but not in published ...
    before = get_all_collections()
    assert ckey in before['staging']
    assert ckey not in before['published']

    # Certify and check the response...
    cert_result = set_certification(api_client, artifact)
    assert cert_result['namespace']['name'] == artifact.namespace
    assert cert_result['name'] == artifact.name
    assert cert_result['version'] == artifact.version
    assert cert_result['href'] is not None
    assert cert_result['metadata']['tags'] == ['tools']

    # wait for move task from `staging` repo to `published` repo
    time.sleep(SLEEP_SECONDS_ONETIME)

    # Make sure it's moved to the right place ...
    after = get_all_collections()
    assert ckey not in after['staging']
    assert ckey in after['published']

    # Make sure an error is thrown if move attempted again ...
    failed = None
    try:
        cert_result = set_certification(api_client, artifact)
        failed = False
    except Exception:
        failed = True
    assert failed
