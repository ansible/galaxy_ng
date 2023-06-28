import pytest
import time

import concurrent.futures

from ..utils import (
    AnsibleDistroAndRepo,
    ansible_galaxy,
    build_collection,
    create_unused_namespace,
    get_client
)
from ..utils.repo_management_utils import search_collection_endpoint
from ..utils.tools import generate_random_string


@pytest.mark.min_hub_version("4.8dev")
# if this is backported, remove the min_hub_version marker
@pytest.mark.deployment_standalone
def test_upload_concurrency(ansible_config, settings, galaxy_client):

    total = 10

    config = ansible_config(profile="admin")
    client = get_client(
        config=config
    )

    # make a repo
    repo_name = f"repo-test-{generate_random_string()}"
    repo = AnsibleDistroAndRepo(
        client,
        repo_name,
    )
    repo_data = repo.get_repo()

    # make 10 namespaces
    namespaces = [create_unused_namespace(client) for x in range(0, total)]

    # make a collection for each namespace
    artifacts = []
    for namespace in namespaces:
        artifact = build_collection(namespace=namespace, name='foo')
        artifacts.append(artifact)

    server_url = config.get('url').rstrip('/') + '/content/' + repo_data['name'] + '/'

    args_list = [f"collection publish -vvvv {x.filename}" for x in artifacts]
    kwargs_list = [{'ansible_config': config, 'server_url': server_url} for x in artifacts]

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

    gc = galaxy_client("admin")

    for x in range(0, 10):
        matches, _ = search_collection_endpoint(
            gc, repository_name=repo_name
        )
        if matches == len(artifacts):
            break
        time.sleep(10)

    assert matches == len(artifacts)
