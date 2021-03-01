from django.urls.base import reverse
from galaxy_ng.app.constants import DeploymentMode
from django.test.utils import override_settings

from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
)
from galaxy_ng.app import models
from .base import BaseTestCase


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
    )
    qs = CollectionVersion.objects.filter(pk=collection_version.pk)
    with repo.new_version() as new_version:
        new_version.add_content(qs)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestCollectionViewsets(BaseTestCase):

    def setUp(self):
        super().setUp()

        self.admin_user = self._create_user("admin")
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.namespace = models.Namespace.objects.create(name='col_namespace')
        self.collection = Collection.objects.create(
            namespace=self.namespace, name='col_collection'
        )
        self.repo = _create_repo(name='col_repo')

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

        # TODO: Upload pulp_ansible/tests/assets collection
        #       or create dummy ContentArtifacts directly

        self.collections_url = reverse(
            'galaxy:api:content:v3:collections-list',
            kwargs={
                'path': self.repo.name,
            }
        )

        self.collections_detail_url = reverse(
            'galaxy:api:content:v3:collections-detail',
            kwargs={
                'path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name
            }
        )

        self.versions_url = reverse(
            'galaxy:api:content:v3:collection-versions-list',
            kwargs={
                'path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name
            }
        )

    def test_collections_list(self):
        """Assert the call to v3/collections returns correct
        collections and versions
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.collections_url)
        self.assertEqual(response.data['meta']['count'], 1)
        self.assertEqual(response.data['data'][0]['deprecated'], False)
        self.assertEqual(
            response.data['data'][0]['highest_version']['version'], '1.1.2'
        )

    def test_collections_detail(self):
        """Assert detail view for v3/collections/namespace/name
        retrurns the same values
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.collections_detail_url)
        self.assertEqual(response.data['namespace'], self.namespace.name)
        self.assertEqual(response.data['deprecated'], False)
        self.assertEqual(
            response.data['highest_version']['version'], '1.1.2'
        )

    def test_collection_versions_list(self):
        """Assert v3/collections/namespace/name/versions/
        lists all available versions.

        Assert that each version href returns correct data and
        artifacts.
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.versions_url)
        self.assertEqual(response.data['meta']['count'], 2)
        self.assertEqual(response.data['data'][0]['version'], '1.1.2')
        self.assertEqual(response.data['data'][1]['version'], '1.1.1')

        # TODO: implement subtests for each version after the
        # upload of artifacts has been implemented in `self.setUp`
        # for version in response.data['data']:
        #     with self.subTest(version=version['version):
        #         vresponse = self.client.get(version['href'])
