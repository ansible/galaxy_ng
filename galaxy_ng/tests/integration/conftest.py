import os
import pytest

from .utils import upload_artifact as _upload_artifact
from .constants import USERNAME_PUBLISHER
from orionutils.generator import build_collection




class AnsibleConfigFixture(dict):

    # This is "kinda" like how IQE uses dynaconf, but
    # much simpler and not such a huge tangled mess to 
    # understand ...
    
    # The class is instantiated with a "namespace" of sorts, 
    # which sets the context for the rest of the config ...
    #   config = ansible_config("ansible_partner")
    #   config = ansible_config("ansible_insights")

    def __init__(self, namespace):
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


@pytest.fixture
def published():
    return {}


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