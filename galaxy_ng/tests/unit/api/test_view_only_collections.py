from django.urls.base import reverse
from django.test.utils import override_settings

from rest_framework.test import APIClient, APITestCase

from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
)
from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode


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
@override_settings(GALAXY_ENABLE_VIEW_ONLY_ACCESS=True)
class ViewOnlyTestCase(APITestCase):
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
            'galaxy:api:content:v3:collections-detail',
            kwargs={
                'path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name
            }
        )

    def test_view_only_access_to_collections(self):
        from galaxy_ng.app.access_control.statements import STANDALONE_STATEMENTS
        response = self.client.get(self.collections_detail_url)
        self.assertEqual(STANDALONE_STATEMENTS['MyUserViewSet'][0]['action'], ['retrieve'])
        self.assertEqual(STANDALONE_STATEMENTS['MyUserViewSet'][0]['principal'], ['*'])
        self.assertEqual(response.data['namespace'], self.namespace.name)
        self.assertEqual(response.data['deprecated'], False)
        self.assertEqual(
            response.data['highest_version']['version'], '1.1.2'
        )
