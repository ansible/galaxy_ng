import uuid

from django.urls.base import reverse
from django.test.utils import override_settings

from rest_framework.test import APIClient
from unittest.mock import patch

from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
)
from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode

from .base import BaseTestCase


class MockSettings:
    """A dictionary like shim that serves as a dynaconf provided settings mock."""
    def __init__(self, kwargs):
        self.kwargs = kwargs
        # every setting should be evaluatable as a property ...
        for k, v in self.kwargs.items():
            setattr(self, k, v)

    def get(self, key, default=None):
        return self.kwargs.get(key, default)


def _create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(
        name=name, base_path=name, repository=repo
    )
    return repo


def _get_create_version_in_repo(namespace, collection, version, repo):
    collection_version, _ = CollectionVersion.objects.get_or_create(
        namespace=namespace,
        name=collection.name,
        collection=collection,
        version=version,
        sha256=uuid.uuid4().hex,
    )
    qs = CollectionVersion.objects.filter(pk=collection_version.pk)
    with repo.new_version() as new_version:
        new_version.add_content(qs)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class ViewOnlyTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

        self.namespace = models.Namespace.objects.create(name='view_only_namespace')
        self.collection = Collection.objects.create(
            namespace=self.namespace, name='view_only_collection'
        )
        self.repo = _create_repo(name='view_only_repo')

        _get_create_version_in_repo(
            self.namespace,
            self.collection,
            '1.1.1',
            self.repo
        )
        _get_create_version_in_repo(
            self.namespace,
            self.collection,
            '1.1.2',
            self.repo
        )

        self.collections_detail_url = reverse(
            'galaxy:api:v3:collections-detail',
            kwargs={
                'distro_base_path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name
            }
        )

        self.ns_url = reverse('galaxy:api:v3:namespaces-list')

        self.ns_detail_url = reverse(
            'galaxy:api:v3:namespaces-detail',
            kwargs={
                "name": self.namespace.name
            }
        )

    def test_unauthenticated_access_to_collections(self):
        response = self.client.get(self.collections_detail_url)
        self.assertEqual(response.data['errors'][0]['status'], '401')
        kwargs = {
            'GALAXY_DEPLOYMENT_MODE': 'standalone',
            'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS': True
        }
        with patch('galaxy_ng.app.access_control.access_policy.settings', MockSettings(kwargs)):
            response = self.client.get(self.collections_detail_url)
            self.assertEqual(response.data['name'], self.collection.name)
            self.assertEqual(response.data['namespace'], self.collection.namespace.name)
            self.assertEqual(response.data['deprecated'], False)
            self.assertEqual(
                response.data['highest_version']['version'], '1.1.2'
            )

    def test_unauthenticated_access_to_namespace(self):
        response = self.client.get(self.ns_detail_url)
        self.assertEqual(response.data['errors'][0]['status'], '401')
        kwargs = {
            'GALAXY_DEPLOYMENT_MODE': 'standalone',
            'GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS': True
        }
        with patch('galaxy_ng.app.access_control.access_policy.settings', MockSettings(kwargs)):
            response = self.client.get(self.ns_detail_url)
            self.assertEqual(response.data['name'], self.namespace.name)
