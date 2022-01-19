import os
import pytest
import shutil

from .utils import upload_artifact as _upload_artifact
from .utils import get_client
from .utils import ansible_galaxy
from .utils import set_certification
from .constants import USERNAME_PUBLISHER
from orionutils.generator import build_collection


MARKER_CONFIG = """
qa: Mark tests to run in the vortex job.
galaxyapi_smoke: Smoke tests for galaxy-api backend.
standalone_only: Tests that should not run against the Insights version of Hub.
cloud_only: Tests that should not run against the standalone version of Hub.
cli: Tests that shell out to the real ansible-galaxy cli.
"""


def pytest_configure(config):
    config.addinitvalue_line('markers', MARKER_CONFIG)


class AnsibleConfigFixture(dict):

    # This is "kinda" like how IQE uses dynaconf, but
    # much simpler and not such a huge tangled mess to 
    # understand ...
    
    # The class is instantiated with a "namespace" of sorts, 
    # which sets the context for the rest of the config ...
    #   config = ansible_config("ansible_partner")
    #   config = ansible_config("ansible_insights")

    def __init__(self, namespace1, namespace=None):
        self.namespace = namespace
    
    def __repr__(self):
        return f'<AnsibleConfigFixture: {self.namespace}>'

    def __getitem__(self, key):

        if key == 'url':
            # The "url" key is actually the full url to the api root.
            return os.environ.get(
                'HUB_API_ROOT',
                'http://localhost:8002/api/automation-hub/'
            )

        elif key == 'auth_url':
            # The auth_url value should be None for a standalone stack.
            return os.environ.get(
                'HUB_AUTH_URL',
                None
            )

        elif key == 'token':
            return os.environ.get(
                'HUB_TOKEN',
                None
            )

        elif key == 'username':
            return os.environ.get(
                'HUB_USERNAME',
                'admin'
            )

        elif key == 'password':
            return os.environ.get(
                'HUB_PASSWORD',
                'admin'
            )

        elif key == 'hub_use_inbound':
            # This value will be compared to "use_distribution" in the 
            # test_api_publish test. I assume it has to do with pulp's
            # concept of "distribution" but not sure what it actually
            # means in this case
            return True

        elif key == 'use_move_endpoint':
            # tells the tests whether or not to try to mark
            # an imported collection as "published". This happens
            # automatically in the default config for standalone,
            # so should return False in that case ...

            if os.environ.get('HUB_USE_MOVE_ENDPOINT'):
                val = os.environ['HUB_USE_MOVE_ENDPOINT']
                if str(val) in ['1', 'True', 'true']:
                    return True

            # standalone ...
            return False

            # cloud ...
            # return True

        else:
            print('')
            print(f'## GET {self.namespace} {key}')
            import epdb; epdb.st()

        return super().__getitem__(key)
    
    def get(self, key):
        return self.__getitem__(key)


class AnsibleAppFixture():
    def __init__(self):
        self.config = AnsibleConfigFixture('APP')
        setattr(
            self.config,
            'AUTOMATION_HUB',
            AnsibleConfigFixture('AUTOMATION_HUB')
        )


@pytest.fixture
def ansible_config():
    return AnsibleConfigFixture


'''
@pytest.fixture
def published():
    return {}
'''

@pytest.fixture(scope="function")
def published(ansible_config, artifact):                                                                                        
    config = ansible_config("ansible_partner", namespace=artifact.namespace)
    ansible_galaxy(
        f"collection publish {artifact.filename} -vvv --server=automation_hub",
        ansible_config=config
    )

    client = get_client(ansible_config("ansible_insights"))
    set_certification(client, artifact)

    return artifact


@pytest.fixture
def app():
    return AnsibleAppFixture()


@pytest.fixture(scope="function")
def artifact():
    """Generate a randomized collection for testing."""

    artifact = build_collection(
        "skeleton",
        config={"namespace": USERNAME_PUBLISHER}
    )
    return artifact


@pytest.fixture
def upload_artifact():
    return _upload_artifact


'''
@pytest.fixture
def cleanup_collections():
    def cleanup(*args, **kwargs):
        import epdb; epdb.st()
        return None
    return cleanup
'''

@pytest.fixture
def cleanup_collections(request):
    """Clean created resources during test executions."""

    def cleanup():
        path = os.path.expanduser(
            f"~/.ansible/collections/ansible_collections/{USERNAME_PUBLISHER}/"
        )
        if os.path.exists(path):
            shutil.rmtree(path)

    request.addfinalizer(cleanup)