"""test_move.py - Tests related to the move api.

See: https://issues.redhat.com/browse/AAH-1268

"""
import pytest
from orionutils.generator import build_collection

from galaxykit.collections import upload_artifact
from galaxykit.utils import wait_for_task as gk_wait_for_task
from ..conftest import is_hub_4_5
from ..constants import USERNAME_PUBLISHER
from ..utils import (
    copy_collection_version,
    get_client,
    set_certification,
    wait_for_task,
    wait_for_url,
)
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
    config = ansible_config("partner_engineer")
    api_prefix = config.get("api_prefix").rstrip("/")
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
            next_page = f'{api_prefix}/_ui/v1/collection-versions/?repository={repo}'
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
    gc_admin = galaxy_client("partner_engineer")
    resp = upload_artifact(None, gc_admin, artifact)
    gk_wait_for_task(gc_admin, resp)
    dest_url = (
        f"content/staging/v3/collections/{artifact.namespace}/"
        f"{artifact.name}/versions/{artifact.version}/"
    )
    wait_for_url(api_client, dest_url)

    # Make sure it ended up in staging but not in published ...
    before = get_all_collections()
    assert ckey in before['staging']
    assert ckey not in before['published']

    # Certify and check the response...
    hub_4_5 = is_hub_4_5(ansible_config)
    cert_result = set_certification(api_client, artifact, hub_4_5=hub_4_5)

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

    config = ansible_config("partner_engineer")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    def get_all_collections():
        collections = {
            'staging': {},
            'community': {}
        }
        for repo in collections.keys():
            next_page = f'{api_prefix}/_ui/v1/collection-versions/?repository={repo}'
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
            "tags": ["tools", "copytest"],
        }
    )
    ckey = (artifact.namespace, artifact.name, artifact.version)
    assert ckey not in pre['staging']
    assert ckey not in pre['community']

    # import and wait ...
    gc_admin = galaxy_client("partner_engineer")
    resp = upload_artifact(None, gc_admin, artifact)
    gk_wait_for_task(gc_admin, resp)
    dest_url = (
        f"content/staging/v3/collections/{artifact.namespace}/"
        f"{artifact.name}/versions/{artifact.version}/"
    )
    wait_for_url(api_client, dest_url)

    # Make sure it ended up in staging ...
    before = get_all_collections()
    assert ckey in before['staging']
    assert ckey not in before['community']

    # Copy the collection to /community/
    copy_result = copy_collection_version(
        api_client,
        artifact,
        src_repo_name="staging",
        dest_repo_name="community"
    )

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

    config = ansible_config("admin")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

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
    gk_wait_for_task(gc_admin, resp)

    # get staging repo version
    staging_repo = api_client(
        f'{api_prefix}/pulp/api/v3/repositories/ansible/ansible/?name=staging'
    )["results"][0]

    pulp_href = staging_repo["pulp_href"]

    collection_version = api_client(
        f'{api_prefix}/pulp/api/v3/content/ansible/collection_versions/'
        f'?namespace={artifact.namespace}&name={artifact.name}&version={artifact.version}'
    )["results"][0]

    cv_href = collection_version["pulp_href"]

    collection = f'content/staging/v3/collections/{artifact.namespace}/{artifact.name}/'
    collection_version = f'{collection}versions/{artifact.version}/'
    collection_mark = (
        f'{api_prefix}/pulp/api/v3/content/ansible/collection_marks/'
        f'?marked_collection={cv_href}'
    )

    col_deprecation = api_client(collection)["deprecated"]
    assert col_deprecation is False

    col_signature = api_client(collection_version)["signatures"]
    assert len(col_signature) == 0

    col_marked = api_client(collection_mark)["results"]
    assert len(col_marked) == 0

    signing_service = api_client(
        f'{api_prefix}/pulp/api/v3/signing-services/?name=ansible-default'
    )["results"][0]

    # sign collection
    signed_collection = api_client(
        f'{pulp_href}sign/',
        args={
            "content_units": [cv_href],
            "signing_service": signing_service["pulp_href"]
        },
        method="POST"
    )

    resp = wait_for_task(api_client, signed_collection)
    assert resp['state'] == 'completed'

    # mark collection
    marked_collection = api_client(
        f'{pulp_href}mark/',
        args={
            "content_units": [cv_href],
            "value": "marked"
        },
        method="POST"
    )

    resp = wait_for_task(api_client, marked_collection)
    assert resp['state'] == 'completed'

    # deprecate collection
    deprecate_collection = api_client(
        f'{api_prefix}/v3/plugin/ansible/content/staging/collections/'
        f'index/{artifact.namespace}/{artifact.name}/',
        args={
            "deprecated": True
        },
        method="PATCH"
    )

    resp = wait_for_task(api_client, deprecate_collection)
    assert resp['state'] == 'completed'

    col_deprecation = api_client(collection)["deprecated"]
    assert col_deprecation is True

    col_signature = api_client(collection_version)["signatures"]
    assert len(col_signature) == 1

    col_marked = api_client(collection_mark)["results"]
    assert len(col_marked) == 1

    # Copy the collection to /community/
    copy_result = copy_collection_version(
        api_client,
        artifact,
        src_repo_name="staging",
        dest_repo_name="community"
    )

    assert copy_result["namespace"]["name"] == artifact.namespace
    assert copy_result["name"] == artifact.name
    assert copy_result["version"] == artifact.version

    collection = f'content/community/v3/collections/{artifact.namespace}/{artifact.name}/'
    collection_version = f'{collection}versions/{artifact.version}/'
    collection_mark = (
        f'{api_prefix}/pulp/api/v3/content/ansible/collection_marks/'
        f'?marked_collection={cv_href}'
    )

    col_deprecation = api_client(collection)["deprecated"]
    assert col_deprecation is True

    col_signature = api_client(collection_version)["signatures"]
    assert len(col_signature) == 1

    assert "marked" in copy_result["marks"]
