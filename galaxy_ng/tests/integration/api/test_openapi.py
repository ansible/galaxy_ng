"""test_openapi.py - Tests related to open api generation and schema.

See: https://issues.redhat.com/browse/AAH-1169

"""

import json
import os
import pytest
import subprocess
import tempfile

from openapi_spec_validator import validate_spec

from ..utils import get_client, is_docker_installed


pytestmark = pytest.mark.qa  # noqa: F821


PULPY_VARIABLES = [
    '{ansible_collection_href}',
    '{ansible_collection_version_href}',
    '{ansible_collection_import_href}',
    '{role_href}',
    '{task_group_href}',
    '{upload_href}',
    '{worker_href}'
]


@pytest.mark.openapi
def test_galaxy_openapi_no_pulp_variables(ansible_config):
    """Tests whether openapi.json has valid path names"""

    config = ansible_config("basic_user")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    galaxy_spec = api_client('/api/automation-hub/v3/openapi.json')
    assert 'paths' in galaxy_spec

    paths_keys = list(galaxy_spec['paths'].keys())
    for path in paths_keys:
        assert not path.startswith('{')


@pytest.mark.openapi
def test_galaxy_openapi_validation(ansible_config):
    """Tests whether openapi.json passes openapi linter"""

    config = ansible_config("basic_user")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    galaxy_spec = api_client('/api/automation-hub/v3/openapi.json')
    validate_spec(galaxy_spec)


@pytest.mark.openapi
def test_pulp_openapi_has_variables(ansible_config):
    """Tests whether openapi.json has valid path names for pulp"""

    config = ansible_config("basic_user")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    pulp_spec = api_client('/api/automation-hub/pulp/api/v3/docs/api.json')
    assert 'paths' in pulp_spec

    paths_keys = list(pulp_spec['paths'].keys())
    for ev in PULPY_VARIABLES:
        assert ev in paths_keys


@pytest.mark.standalone_only
@pytest.mark.openapi
@pytest.mark.openapi_generate_bindings
@pytest.mark.skipif(not is_docker_installed(), reason="docker is not installed on this machine")
def test_openapi_bindings_generation(ansible_config):
    """Verify client bindings can be built from the pulp'ish api spec"""

    config = ansible_config("basic_user")
    api_client = get_client(
        config=config,
        request_token=True,
        require_auth=True
    )

    pulp_spec = api_client('/api/automation-hub/pulp/api/v3/docs/api.json')
    status = api_client('/api/automation-hub/pulp/api/v3/status/')
    version = [x['version'] for x in status['versions'] if x['component'] == 'galaxy'][0]
    my_id = subprocess.run(
        'id -u',
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).stdout.decode('utf-8').strip()
    volume_name = '/local'
    generator_repo = 'https://github.com/pulp/pulp-openapi-generator'

    with tempfile.TemporaryDirectory(prefix='galaxy-bindings-') as output_dir:

        generator_checkout = os.path.join(output_dir, 'pulp-openapi-generator')
        clone_pid = subprocess.run(
            f'git clone {generator_repo} {generator_checkout}',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        assert clone_pid.returncode == 0, clone_pid.stderr.decode('utf-8')

        with open(os.path.join(generator_checkout, 'api.json'), 'w') as f:
            f.write(json.dumps(pulp_spec))

        properties = '--additional-properties=packageName=pulpcore.client.galaxy_ng'
        properties += ',projectName=galaxy_ng-client'
        properties += f',packageVersion={version}'

        cmd = [
            'docker',
            'run',
            '--ulimit', 'nofile=122880:122880',
            '-u',
            my_id,
            '--rm',
            '-v',
            f'{generator_checkout}:{volume_name}',
            'openapitools/openapi-generator-cli:v4.3.1',
            'generate',
            '-i', '/local/api.json',
            '-g', 'python',
            '-o', '/local/galaxy_ng-client',
            properties,
            '-t', '/local/templates/python',
            '--skip-validate-spec',
            '--strict-spec=false'
        ]

        docker_pid = subprocess.run(
            ' '.join(cmd),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        assert docker_pid.returncode == 0, docker_pid.stderr.decode('utf-8')
        assert os.path.exists(os.path.join(generator_checkout, 'galaxy_ng-client'))
