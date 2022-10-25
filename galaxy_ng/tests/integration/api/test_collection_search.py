import random
import string
import time

import pytest
from ansible.galaxy.api import GalaxyError

from galaxy_ng.tests.integration.constants import SLEEP_SECONDS_ONETIME

from ..utils import (
    build_collection,
    cleanup_namespace,
    create_namespace,
    create_unused_namespace,
    generate_namespace,
    get_all_collections_by_repo,
    get_all_repository_collection_versions,
    get_client,
    set_certification,
    upload_artifact,
    wait_for_task,
)

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.search
@pytest.mark.collection_search
def test_search_collections(ansible_config):

    config = ansible_config("partner_engineer")
    api_prefix = config.get("api_prefix").rstrip("/")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    # delete all namespaces & collections
    repoversions = get_all_repository_collection_versions(api_client)
    to_delete_namespaces = sorted(set([x[1] for x in repoversions.keys()]))
    for namespace_name in to_delete_namespaces:
        try:
            cleanup_namespace(namespace_name, api_client=api_client)
        except Exception as e:
            pass

    # define some collections
    specs = [
        ('community', 'cloud', '1.0.0', ['tag1']),
        ('ibm', 'blue', '2.0.0', ['tag2']),
        ('redhat', 'red', '3.0.0', ['tag3']),
        ('alma', 'notred', '4.0.0', ['tag4']),
        # ('community', 'cloud', '1.0.1'),
    ]

    # make the namespaces
    namespaces = [x[0] for x in specs]
    for namespace_name in namespaces:
        cleanup_namespace(namespace_name, api_client=api_client)
        create_namespace(namespace_name, api_client=api_client)

    # make some collections and publish them ...
    cmap = {}
    for spec in specs:
        namespace_name = spec[0]
        collection_name = spec[1]
        collection_version = spec[2]
        if len(spec) > 3:
            tags = spec[3]
        else:
            tags = []

        artifact = build_collection(
            namespace=namespace_name,
            name=collection_name,
            version=collection_version,
            tags=tags,
            roles=[],
            readme='',
            description='',
            use_orionutils=False
        )
        cmap[(namespace_name, collection_name, collection_version)] = artifact
        resp = upload_artifact(config, api_client, artifact)
        wait_for_task(api_client, resp)
        set_certification(api_client, artifact)

        # check tags ...
        _cversions = get_all_repository_collection_versions(api_client)
        ds = _cversions[tuple(['published'] + list(spec[:3]))]
        cvdata = api_client(ds['href'])
        #import epdb; epdb.st()
        assert len(cvdata['metadata']['tags']) == len(tags), cvdata['metdata']['tags']
        #import epdb; epdb.st()

    # .../api/_ui/v1/repo/community/?keywords=foreman&deprecated=false&offset=0&limit=10

    # search by namespace name
    for namespace_name in namespaces:
        expected = [x for x in specs if x[0] == namespace_name]
        search_url = api_prefix + '/' + '_ui/v1/repo/published/' + '?' + 'keywords=' + namespace_name
        resp = api_client(search_url)
        assert resp['meta']['count'] == len(expected), f'failed searching for {namespace_name}'

    # search by collection name
    for spec in specs:
        collection_name = spec[1]
        search_url = api_prefix + '/' + '_ui/v1/repo/published/' + '?' + 'keywords=' + collection_name
        resp = api_client(search_url)
        assert resp['meta']['count'] == 1, f'failed searching for {collection_name}'

    import epdb; epdb.st()

