import pytest

import concurrent.futures

from ..utils import (
    AnsibleDistroAndRepo,
    ansible_galaxy,
    build_collection,
    create_unused_namespace,
    get_client, gen_string,
)


@pytest.mark.standalone_only
def test_upload_concurrency(ansible_config, settings, galaxy_client):

    total = 10

    config = ansible_config(profile="admin")
    client = get_client(
        config=config
    )

    # make a repo
    repo = AnsibleDistroAndRepo(
        client,
        gen_string(),
    )
    repo_data = repo.get_repo()
    repo_name = repo_data['name']

    # make 10 namespaces
    namespaces = [create_unused_namespace(client) for x in range(0, total + 1)]

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
    cvs = gc.get(
        (
            "/api/automation-hub/v3/plugin/ansible/search/collection-versions/"
            + f"?repository_name={repo_name}"
        )
    )

    assert cvs['meta']['count'] == len(artifacts)
