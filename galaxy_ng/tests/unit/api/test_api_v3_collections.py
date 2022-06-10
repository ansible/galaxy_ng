import logging
from unittest.case import skip
from uuid import uuid4

from django.test.utils import override_settings
from django.urls.base import reverse
from orionutils.generator import build_collection
from pulp_ansible.app.models import (
    AnsibleDistribution,
    AnsibleRepository,
    Collection,
    CollectionVersion,
)

from pulp_ansible.app.galaxy.v3.views import get_collection_dependents, get_unique_dependents

from rest_framework import status

from galaxy_ng.app import models
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.tests.constants import TEST_COLLECTION_CONFIGS

from .base import BaseTestCase

log = logging.getLogger(__name__)


def _create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(
        name=name, base_path=name, repository=repo
    )
    return repo


def _get_create_version_in_repo(namespace, collection, repo, **kwargs):
    collection_version, _ = CollectionVersion.objects.get_or_create(
        namespace=namespace,
        name=collection.name,
        collection=collection,
        **kwargs,
    )
    qs = CollectionVersion.objects.filter(pk=collection_version.pk)
    with repo.new_version() as new_version:
        new_version.add_content(qs)
    return collection_version


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

        self.version_1_1_1 = _get_create_version_in_repo(
            self.namespace,
            self.collection,
            self.repo,
            version="1.1.1",
        )
        _get_create_version_in_repo(
            self.namespace,
            self.collection,
            self.repo,
            version="1.1.2",
        )

        # TODO: Upload pulp_ansible/tests/assets collection
        #       or create dummy ContentArtifacts directly

        self.collections_url = reverse(
            'galaxy:api:v3:collections-list',
            kwargs={
                'distro_base_path': self.repo.name,
            }
        )

        self.collections_detail_url = reverse(
            'galaxy:api:v3:collections-detail',
            kwargs={
                'distro_base_path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name
            }
        )

        self.versions_url = reverse(
            'galaxy:api:v3:collection-versions-list',
            kwargs={
                'distro_base_path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name
            }
        )

        self.versions_detail_url = reverse(
            'galaxy:api:v3:collection-versions-detail',
            kwargs={
                'distro_base_path': self.repo.name,
                'namespace': self.namespace.name,
                'name': self.collection.name,
                'version': '1.1.2'
            }
        )

        self.collection_upload_url = reverse(
            "galaxy:api:v3:collection-artifact-upload"
        )

        # The following tests use endpoints related to
        # issue https://issues.redhat.com/browse/AAH-224
        # For now endpoints are temporary deactivated
        # self.all_collections_url = reverse(
        #     "galaxy:api:v3:all-collections-list",
        #     kwargs={
        #         "distro_base_path": self.repo.name,
        #     },
        # )
        #
        # self.all_versions_url = reverse(
        #     "galaxy:api:v3:all-collection-versions-list",
        #     kwargs={
        #         "distro_base_path": self.repo.name,
        #     },
        # )
        #
        # self.metadata_url = reverse(
        #     "galaxy:api:v3:repo-metadata",
        #     kwargs={
        #         "distro_base_path": self.repo.name,
        #     },
        # )

        # used for href tests
        self.pulp_href_fragment = "pulp_ansible/galaxy"

    def upload_collections(self, namespace=None, collection_configs=None):
        """using the config from TEST_COLLECTION_CONFIGS,
        generates and uploads collections to pulp_ansible/galaxy.
        """
        collection_configs = collection_configs or TEST_COLLECTION_CONFIGS
        self._create_namespace(namespace, groups=[self.pe_group])
        collections = []
        for config in collection_configs:
            config["namespace"] = namespace
            collection = build_collection("skeleton", config=config)
            response = self.client.post(
                self.collection_upload_url, {"file": open(collection.filename, "rb")}
            )
            collections.append((collection, response))
        return collections

    def test_upload_collection(self):
        """Test successful upload of collections generated with orionutils.

        NOTE: This test is testing only the upload view of the collection
              After the collection is uploaded a pulp task is created to import it.
              but there are no workers running, so the import task is not executed.

        TODO: Call the move/promote of task manually or find a way to execute a eager worker.
              (or even better, move this tests to functional testing)
        """

        self.client.force_authenticate(user=self.admin_user)
        collections = self.upload_collections(namespace=uuid4().hex)
        self.assertEqual(len(collections), 12)
        # assert each collection returned a 202
        for collection in collections:
            self.assertEqual(collection[1].status_code, 202)
        # Upload is performed but the collection is not yet imported

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

        # Ensure href is overwritten
        self.assertNotIn(self.pulp_href_fragment, response.data["data"][0]["href"])
        self.assertNotIn(self.pulp_href_fragment, response.data["data"][0]["versions_url"])
        self.assertNotIn(
            self.pulp_href_fragment, response.data["data"][0]["highest_version"]["href"]
        )

    @skip("https://issues.redhat.com/browse/AAH-224")
    def test_unpaginated_collections_list(self):
        """Assert the call to v3/collections/all returns correct
        collections and versions
        """
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.all_collections_url)
        self.assertEqual(response.data[0]['deprecated'], False)
        self.assertEqual(response.data[0]['highest_version']['version'], '1.1.2')

        # Ensure href is overwritten
        self.assertNotIn(self.pulp_href_fragment, response.data[0]["href"])
        self.assertNotIn(self.pulp_href_fragment, response.data[0]["versions_url"])
        self.assertNotIn(self.pulp_href_fragment, response.data[0]["highest_version"]["href"])

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

        # Ensure hrefs are overwritten
        self.assertNotIn(self.pulp_href_fragment, response.data["href"])
        self.assertNotIn(self.pulp_href_fragment, response.data["versions_url"])
        self.assertNotIn(self.pulp_href_fragment, response.data["highest_version"]["href"])

        # Check response after DELETE
        response = self.client.delete(self.collections_detail_url)
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("task", response.data.keys())

    def test_collection_version_delete_dependency_check_positive_match(self):
        baz_collection = Collection.objects.create(namespace=self.namespace, name="baz")
        # need versions that match 1.1.1, but not 1.1.2
        for counter, dep_version in enumerate(["1.1.1", "<1.1.2", ">0.0.0,<=1.1.1"]):
            baz_version = _get_create_version_in_repo(
                self.namespace,
                baz_collection,
                self.repo,
                version=counter,
                dependencies={f"{self.namespace.name}.{self.collection.name}": dep_version},
            )
            self.assertIn(baz_version, get_unique_dependents(self.version_1_1_1))

    def test_collection_version_delete_dependency_check_negative_match(self):
        baz_collection = Collection.objects.create(namespace=self.namespace, name="baz")
        for counter, dep_version in enumerate(["1.1.2", ">1", "<1.1.1", "~=2"]):
            baz_version = _get_create_version_in_repo(
                self.namespace,
                baz_collection,
                self.repo,
                version=counter,
                dependencies={f"{self.namespace.name}.{self.collection.name}": dep_version},
            )
            self.assertNotIn(baz_version, get_unique_dependents(self.version_1_1_1))

    def test_collection_delete_dependency_check(self):
        baz_collection = Collection.objects.create(namespace=self.namespace, name="baz")
        for counter, dep_version in enumerate(["1.1.1", ">=1", "<2", "~1", "*"]):
            baz_version = _get_create_version_in_repo(
                self.namespace,
                baz_collection,
                self.repo,
                version=counter,
                dependencies={f"{self.namespace.name}.{self.collection.name}": dep_version},
            )
            self.assertIn(baz_version, get_collection_dependents(self.collection))
        self.assertFalse(get_collection_dependents(baz_collection))

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

        # Ensure hrefs are overwritten
        self.assertNotIn(self.pulp_href_fragment, response.data["data"][0]["href"])

        # TODO: implement subtests for each version after the
        # upload of artifacts has been implemented in `self.setUp`
        # for version in response.data['data']:
        #     with self.subTest(version=version['version):
        #         vresponse = self.client.get(version['href'])
        #         self.assertNotIn(self.pulp_href_fragment, vresponse.data["href"])
        #         self.assertNotIn(self.pulp_href_fragment, vresponse.data["collection"]["href"])
        #         self.assertNotIn(self.pulp_href_fragment, vresponse.data["download_url"])

    # def test_unpaginated_collection_versions_list(self):
    #     """Assert the call to v3/collections/all returns correct
    #     collections and versions
    #     """
    #     self.client.force_authenticate(user=self.admin_user)
    #     response = self.client.get(self.all_versions_url)
    #     self.assertEqual(response.data[0]['version'], '1.1.2')

    #     # Ensure href is overwritten
    #     self.assertNotIn(self.pulp_href_fragment, response.data[0]["href"])
    #     self.assertNotIn(self.pulp_href_fragment, response.data[0]["collection"]["href"])
    #     self.assertNotIn(self.pulp_href_fragment, response.data[0]["download_url"])

    #     # Ensure some fields are in
    #     for field in ('metadata', 'namespace', 'name', 'artifact'):
    #         with self.subTest(field=field):
    #             self.assertIn(field, response.data[0])

    #     # Ensure some fields are not in
    #     for field in ('manifest', 'files'):
    #         with self.subTest(field=field):
    #             self.assertNotIn(field, response.data[0])
