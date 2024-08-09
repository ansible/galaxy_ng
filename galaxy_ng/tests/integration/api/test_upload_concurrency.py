import pytest
import time

import concurrent.futures

from ..utils import (
    ansible_galaxy,
    build_collection
)
from ..utils.repo_management_utils import search_collection_endpoint, create_repo_and_dist, \
    create_test_namespace
from ..utils.tools import generate_random_string
from ..utils.iqe_utils import aap_gateway


@pytest.mark.min_hub_version("4.8dev")
# if this is backported, remove the min_hub_version marker
@pytest.mark.deployment_standalone
@pytest.mark.skipif(aap_gateway(), reason="This test does not work with the jwt proxy")
def test_upload_concurrency(ansible_config, settings, galaxy_client):

    total = 10

    gc = galaxy_client("admin")

    # make a repo
    repo_name = f"repo-test-{generate_random_string()}"
    create_repo_and_dist(gc, repo_name)  # publishing fails 504 gateway error

    # make 10 namespaces
    namespaces = [create_test_namespace(gc) for x in range(0, total)]

    # make a collection for each namespace
    artifacts = []
    for namespace in namespaces:
        artifact = build_collection(namespace=namespace, name='foo')
        artifacts.append(artifact)

    server_url = gc.galaxy_root + 'content/' + repo_name + '/'

    args_list = [f"collection publish -vvvv {x.filename}" for x in artifacts]
    kwargs_list = [{'galaxy_client': gc, 'server_url': server_url, 'server': repo_name}
                   for x in artifacts]

    with concurrent.futures.ThreadPoolExecutor(max_workers=total) as executor:

        future_to_args_kwargs = {
            executor.submit(ansible_galaxy, args, **kwargs): (args, kwargs)
            for args, kwargs in zip(args_list, kwargs_list)
        }

        for future in concurrent.futures.as_completed(future_to_args_kwargs):
            args, kwargs = future_to_args_kwargs[future]
            try:
                result = future.result()
            except Exception as exc:
                print(f"Function raised an exception: {exc}")
            else:
                print(f"Function returned: {result}")

    for x in range(0, 10):
        matches, _ = search_collection_endpoint(
            gc, repository_name=repo_name
        )
        if matches == len(artifacts):
            break
        time.sleep(10)

    assert matches == len(artifacts)
