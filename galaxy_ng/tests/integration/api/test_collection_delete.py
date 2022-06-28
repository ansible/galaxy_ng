"""test_collection_delete.py - Tests related to collection deletion.
"""

import time

import pytest
from ansible.galaxy.api import GalaxyError

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME

from ..utils import (
    get_all_collections_by_repo,
    get_all_repository_collection_versions,
    get_client,
    wait_for_task,
)

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.delete
@pytest.mark.collection_delete
def test_delete_collection(ansible_config, uncertifiedv2):
    """Tests whether a colleciton can be deleted"""

    config = ansible_config("partner_engineer")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # Enumerate published collection info ...
    collectionv1 = uncertifiedv2[0]
    cnamespace = collectionv1.namespace
    cname = collectionv1.name
    ckeys = []
    for cv in uncertifiedv2:
        ckeys.append((cv.namespace, cv.name, cv.version))

    # Try deleting the whole collection ...
    resp = api_client(
        ('/api/automation-hub/v3/plugin/ansible/content'
         f'/published/collections/index/{cnamespace}/{cname}/'),
        method='DELETE'
    )

    # wait for the orphan_cleanup job to finish ...
    try:
        wait_for_task(api_client, resp, timeout=10000)
    except GalaxyError as ge:
        # FIXME - pulp tasks do not seem to accept token auth
        if ge.http_code in [403, 404]:
            time.sleep(SLEEP_SECONDS_ONETIME)
        else:
            raise Exception(ge)

    # Make sure they're all gone ...
    after = get_all_collections_by_repo(api_client)
    for ckey in ckeys:
        assert ckey not in after['staging']
        assert ckey not in after['published']

    # Does the collection still exist?
    failed = None
    try:
        api_client(f'/api/automation-hub/collections/{cnamespace}/{cname}/')
        failed = False
    except GalaxyError as ge:
        if ge.http_code in [403, 404]:
            failed = True
        else:
            raise Exception(ge)

    assert failed


@pytest.mark.galaxyapi_smoke
@pytest.mark.delete
@pytest.mark.collection_version_delete
def test_delete_collection_version(ansible_config, upload_artifact, uncertifiedv2):
    """Tests whether a colleciton version can be deleted"""

    config = ansible_config("partner_engineer")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    cv_before = get_all_repository_collection_versions(api_client)

    # Enumerate published collection info ...
    collectionv1 = uncertifiedv2[0]
    cnamespace = collectionv1.namespace
    cname = collectionv1.name

    # Delete each collection version from it's repo
    # specific href ...
    ckeys = []
    for cv in uncertifiedv2:
        ckey = (cv.namespace, cv.name, cv.version)
        ckeys.append(ckey)
        matches = []
        for k, v in cv_before.items():
            if k[1:] == ckey:
                matches.append(k)
        for rcv in matches:
            rcv_url = cv_before[rcv]['href']
            resp = api_client(rcv_url, method='DELETE')

            # wait for the orphan_cleanup job to finish ...
            try:
                wait_for_task(api_client, resp, timeout=10000)
            except GalaxyError as ge:
                # FIXME - pulp tasks do not seem to accept token auth
                if ge.http_code in [403, 404]:
                    time.sleep(SLEEP_SECONDS_ONETIME)
                else:
                    raise Exception(ge)

    # make sure the collection-versions are gone ...
    cv_after = get_all_repository_collection_versions(api_client)
    for ckey in ckeys:
        matches = []
        for k, v in cv_after.items():
            if k[1:] == ckey:
                matches.append(k)
        assert len(matches) == 0

    # make sure the collection was automatically purged
    # since all of it's children were deleted ...
    failed = None
    try:
        api_client(f'/api/automation-hub/collections/{cnamespace}/{cname}/')
        failed = False
    except GalaxyError as ge:
        if ge.http_code in [403, 404]:
            failed = True
        else:
            raise Exception(ge)

    assert failed

    assert failed
