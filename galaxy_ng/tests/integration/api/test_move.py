"""test_move.py - Tests related to the move api.

See: https://issues.redhat.com/browse/AAH-1268

"""
import pytest
from orionutils.generator import build_collection

from galaxykit.collections import upload_artifact, move_or_copy_collection, sign_collection, deprecate_collection
from galaxykit.repositories import get_repository_href
from galaxykit.utils import wait_for_task, wait_for_url
from ..conftest import is_hub_4_5
from ..constants import USERNAME_PUBLISHER
from ..utils import set_certification
from ..utils.iqe_utils import is_ocp_env

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.certification
@pytest.mark.collection_move
@pytest.mark.move
@pytest.mark.slow_in_cloud
@pytest.mark.all
def test_move_collection_version(ansible_config, galaxy_client):
    """Tests whether a collection can be moved from repo to repo"""
    gc_admin = galaxy_client("partner_engineer")

    def get_all_collections():
        collections = {
            'staging': {},
            'published': {}
        }
        for repo in collections.keys():
            next_page = f'_ui/v1/collection-versions/?repository={repo}'
            while next_page:
                resp = gc_admin.get(next_page)
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
    resp = upload_artifact(None, gc_admin, artifact)
    wait_for_task(gc_admin, resp)
    dest_url = (
        f"content/staging/v3/collections/{artifact.namespace}/"
        f"{artifact.name}/versions/{artifact.version}/"
    )
    wait_for_url(gc_admin, dest_url)

    # Make sure it ended up in staging but not in published ...
    before = get_all_collections()
    assert ckey in before['staging']
    assert ckey not in before['published']

    # Certify and check the response...
    hub_4_5 = is_hub_4_5(ansible_config)
    cert_result = set_certification(ansible_config(), gc_admin, artifact, hub_4_5=hub_4_5)

    assert cert_result['namespace']['name'] == artifact.namespace
    assert cert_result['name'] == artifact.name
    assert cert_result['version'] == artifact.version
    assert cert_result['href'] is not None
    assert cert_result['metadata']['tags'] == ['tools']

    # Make sure it's moved to the right place ...
    after = get_all_collections()
    assert ckey not in after['staging']
    assert ckey in after['published']

    # Make sure an error is thrown if move attempted again ...

    # uncomment this code when stage performance issues are solved. Because
    # of these problems, the timeout to wait for the certification is very high, making
    # this last verification very long (10 minutes)
    '''
    failed = None
    try:
        cert_result = set_certification(api_client, artifact)
        failed = False
    except Exception:
        failed = True
    assert failed
    '''


@pytest.mark.galaxyapi_smoke
@pytest.mark.certification
@pytest.mark.collection_move
@pytest.mark.move
@pytest.mark.slow_in_cloud
@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.all
def test_copy_collection_version(ansible_config, galaxy_client):
    """Tests whether a collection can be copied from repo to repo"""

    gc_admin = galaxy_client("partner_engineer")

    def get_all_collections():
        collections = {
            'staging': {},
            'community': {}
        }
        for repo in collections.keys():
            next_page = f'_ui/v1/collection-versions/?repository={repo}'
            while next_page:
                resp = gc_admin.get(next_page)
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
            "tags": ["tools", "copytest"],
        }
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)
    assert ckey not in pre['staging']
    assert ckey not in pre['community']

    # import and wait ...
    resp = upload_artifact(None, gc_admin, artifact)
    wait_for_task(gc_admin, resp)
    dest_url = (
        f"content/staging/v3/collections/{artifact.namespace}/"
        f"{artifact.name}/versions/{artifact.version}/"
    )
    wait_for_url(gc_admin, dest_url)

    # Make sure it ended up in staging ...
    before = get_all_collections()
    assert ckey in before['staging']
    assert ckey not in before['community']

    # Copy the collection to /community/
    copy_result = move_or_copy_collection(gc_admin, artifact.namespace, artifact.name,
                                          destination="community", operation="copy")

    # Check the response...
    assert copy_result["namespace"]["name"] == artifact.namespace
    assert copy_result["name"] == artifact.name
    assert copy_result["version"] == artifact.version
    assert copy_result["href"] is not None
    expected_tags = ["tools", "copytest"]
    actual_tags = copy_result["metadata"]["tags"]
    assert sorted(actual_tags) == sorted(expected_tags)

    assert len(copy_result["signatures"]) == 0

    # Make sure it's copied and not moved
    after = get_all_collections()
    assert ckey in after['staging']
    assert ckey in after['community']


@pytest.mark.deployment_standalone
@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.skipif(is_ocp_env(), reason="Content signing not enabled in AAP Operator")
def test_copy_associated_content(ansible_config, galaxy_client):
    """Tests whether a collection and associated content is copied from repo to repo"""

    # TODO: add check for ansible namespace metadata

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["tools", "copytest"],
        }
    )

    # import and wait ...
    gc_admin = galaxy_client("admin")
    resp = upload_artifact(None, gc_admin, artifact)
    wait_for_task(gc_admin, resp)

    # get staging repo version
    pulp_href = get_repository_href(gc_admin, "staging")

    collection_version = gc_admin.get(
        f'pulp/api/v3/content/ansible/collection_versions/'
        f'?namespace={artifact.namespace}&name={artifact.name}&version={artifact.version}'
    )["results"][0]

    cv_href = collection_version["pulp_href"]

    collection = f'content/staging/v3/collections/{artifact.namespace}/{artifact.name}/'
    collection_version = f'{collection}versions/{artifact.version}/'
    collection_mark = (
        f'pulp/api/v3/content/ansible/collection_marks/'
        f'?marked_collection={cv_href}'
    )

    col_deprecation = gc_admin.get(collection)["deprecated"]
    assert col_deprecation is False

    col_signature = gc_admin.get(collection_version)["signatures"]
    assert len(col_signature) == 0

    col_marked = gc_admin.get(collection_mark)["results"]
    assert len(col_marked) == 0

    sign_collection(gc_admin, cv_href, pulp_href)

    # mark collection
    marked_collection = gc_admin.post(
        f'{pulp_href}mark/',
        body={
            "content_units": [cv_href],
            "value": "marked"
        }
    )

    resp = wait_for_task(gc_admin, marked_collection)
    assert resp['state'] == 'completed'

    # deprecate collection
    deprecate_collection(gc_admin, artifact.namespace, artifact.name, "staging")

    col_deprecation = gc_admin.get(collection)["deprecated"]
    assert col_deprecation is True

    col_signature = gc_admin.get(collection_version)["signatures"]
    assert len(col_signature) == 1

    col_marked = gc_admin.get(collection_mark)["results"]
    assert len(col_marked) == 1

    # Copy the collection to /community/
    copy_result = move_or_copy_collection(gc_admin, artifact.namespace, artifact.name,
                                          destination="community", operation="copy")

    assert copy_result["namespace"]["name"] == artifact.namespace
    assert copy_result["name"] == artifact.name
    assert copy_result["version"] == artifact.version

    collection = f'content/community/v3/collections/{artifact.namespace}/{artifact.name}/'
    collection_version = f'{collection}versions/{artifact.version}/'
    collection_mark = (
        f'pulp/api/v3/content/ansible/collection_marks/'
        f'?marked_collection={cv_href}'
    )

    col_deprecation = gc_admin.get(collection)["deprecated"]
    assert col_deprecation is True

    col_signature = gc_admin.get(collection_version)["signatures"]
    assert len(col_signature) == 1

    col_marked = gc_admin.get(collection_mark)["results"]
    assert len(col_marked) == 1

    assert "marked" in copy_result["marks"]
