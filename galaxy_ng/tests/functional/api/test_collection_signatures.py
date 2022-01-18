"""Tests functionality around Collection-Version Signatures."""
from pulp_smash.pulp3.bindings import delete_orphans, monitor_task
from pulp_ansible.tests.functional.utils import (
    create_signing_service,
    delete_signing_service,
    gen_repo,
    gen_ansible_remote,
    get_content,
    SyncHelpersMixin,
    TestCaseUsingBindings,
    skip_if,
)
from pulp_ansible.tests.functional.constants import TEST_COLLECTION_CONFIGS
from orionutils.generator import build_collection
from pulpcore.client.pulp_ansible import AnsibleCollectionsApi, ContentCollectionSignaturesApi
from pulp_ansible.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class CRUDCollectionVersionSignatures(TestCaseUsingBindings, SyncHelpersMixin):
    """
    CRUD CollectionVersionSignatures

    This test targets the following issues:

    * `Pulp #757 <https://github.com/pulp/pulp_ansible/issues/757>`_
    * `Pulp #758 <https://github.com/pulp/pulp_ansible/issues/758>`_
    """

    @classmethod
    def setUpClass(cls):
        """Sets up signing service used for creating signatures."""
        super().setUpClass()
        delete_orphans()
        cls.signing_service = create_signing_service()
        cls.collections = []
        cls.signed_collections = []
        cls.repo = {}
        cls.sig_api = ContentCollectionSignaturesApi(cls.client)
        col_api = AnsibleCollectionsApi(cls.client)
        for i in range(4):
            collection = build_collection("skeleton", config=TEST_COLLECTION_CONFIGS[i])
            response = col_api.upload_collection(collection.filename)
            task = monitor_task(response.task)
            cls.collections.append(task.created_resources[0])

    @classmethod
    def tearDownClass(cls):
        """Deletes repository and removes any content and signatures."""
        monitor_task(cls.repo_api.delete(cls.repo["pulp_href"]).task)
        delete_signing_service(cls.signing_service.name)
        delete_orphans()

    def test_01_create_signed_collections(self):
        """Test collection signatures can be created through the sign task."""
        repo = self.repo_api.create(gen_repo())
        body = {"add_content_units": self.collections}
        monitor_task(self.repo_api.modify(repo.pulp_href, body).task)

        body = {"content_units": self.collections, "signing_service": self.signing_service.pulp_href}
        monitor_task(self.repo_api.sign(repo.pulp_href, body).task)
        repo = self.repo_api.read(repo.pulp_href)
        self.repo.update(repo.to_dict())

        self.assertEqual(int(repo.latest_version_href[-2]), 2)
        content_response = get_content(self.repo)
        self.assertIn("ansible.collection_signature", content_response)
        self.assertEqual(len(content_response["ansible.collection_signature"]), 4)
        self.signed_collections.extend(content_response["ansible.collection_signature"])

    @skip_if(bool, "signed_collections", False)
    def test_02_read_signed_collection(self):
        """Test that a collection's signature can be read."""
        signature = self.sig_api.read(self.signed_collections[0]["pulp_href"])
        self.assertIn(signature.signed_collection, self.collections)
        self.assertEqual(signature.signing_service, self.signing_service.pulp_href)

    @skip_if(bool, "signed_collections", False)
    def test_03_read_signed_collections(self):
        """Test that collection signatures can be listed."""
        signatures = self.sig_api.list(repository_version=self.repo["latest_version_href"])
        self.assertEqual(signatures.count, len(self.signed_collections))
        signature_set = set([s.pulp_href for s in signatures.results])
        self.assertEqual(signature_set, {s["pulp_href"] for s in self.signed_collections})

    @skip_if(bool, "signed_collections", False)
    def test_04_partially_update(self):
        """Attempt to update a content unit using HTTP PATCH.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = {"pubkey_fingerprint": "testing"}
        with self.assertRaises(AttributeError) as exc:
            self.sig_api.partial_update(self.signed_collections[0], attrs)
        msg = "object has no attribute 'partial_update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "signed_collections", False)
    def test_05_fully_update(self):
        """Attempt to update a content unit using HTTP PUT.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        attrs = {"pubkey_fingerprint": "testing"}
        with self.assertRaises(AttributeError) as exc:
            self.sig_api.update(self.signed_collections[0]["pulp_href"], attrs)
        msg = "object has no attribute 'update'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "signed_collections", False)
    def test_06_delete(self):
        """Attempt to delete a content unit using HTTP DELETE.

        This HTTP method is not supported and a HTTP exception is expected.
        """
        with self.assertRaises(AttributeError) as exc:
            self.sig_api.delete(self.signed_collections[0]["pulp_href"])
        msg = "object has no attribute 'delete'"
        self.assertIn(msg, exc.exception.args[0])

    @skip_if(bool, "signed_collections", False)
    def test_07_duplicate(self):
        """Attempt to create a signature duplicate"""
        body = {"content_units": self.collections, "signing_service": self.signing_service.pulp_href}
        result = monitor_task(self.repo_api.sign(self.repo["pulp_href"], body).task)
        repo = self.repo_api.read(self.repo["pulp_href"])

        self.assertEqual(repo.latest_version_href, self.repo["latest_version_href"])
        self.assertEqual(len(result.created_resources), 0)