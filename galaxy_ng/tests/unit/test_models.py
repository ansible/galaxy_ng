from galaxy_ng.app.constants import INBOUND_REPO_NAME_FORMAT
from django.test import TestCase
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, Collection

from galaxy_ng.app.models import Namespace


class TestSignalCreateRepository(TestCase):
    def test_create_repository_ensure_retain_repo_versions(self):
        """On creation retain_repo_versions is set to 1 if omited"""
        repo_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name="test")
        repository = AnsibleRepository.objects.create(name=repo_name)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 1)

    def test_when_set_not_changed_retain_repo_versions(self):
        """On creation retain_repo_versions is not changed when explicit set"""
        repo_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name="test2")
        repository = AnsibleRepository.objects.create(name=repo_name, retain_repo_versions=99)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 99)

    def test_update_do_not_change_retain_repo_versions(self):
        """On update retain_repo_versions is not changed when already exists"""
        # Create repo setting retain_repo_versions
        repo_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name="test3")
        repository = AnsibleRepository.objects.create(name=repo_name, retain_repo_versions=99)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 99)
        # Update the name of the repo
        AnsibleRepository.objects.filter(pk=repository.pk).update(name="test3_2")
        updated = AnsibleRepository.objects.get(pk=repository.pk)
        # Ensure name changed but retain_repo_versions did not
        self.assertEqual(updated.name, "test3_2")
        self.assertEqual(updated.retain_repo_versions, 99)


class TestSignalCreateNamespace(TestCase):
    namespace_name = 'my_test_ns'

    def test_new_collection_create_namespace(self):
        self.assertFalse(Namespace.objects.filter(name=self.namespace_name))
        Collection.objects.create(
            name='my_collection',
            namespace=self.namespace_name,
        )
        self.assertTrue(Namespace.objects.filter(name=self.namespace_name))

    def test_existing_namespace_not_changed(self):
        description = 'Namespace created not by signal'
        Namespace.objects.create(
            name=self.namespace_name,
            description=description,
        )
        Collection.objects.create(
            name='my_collection',
            namespace=self.namespace_name,
        )
        namespace = Namespace.objects.get(name=self.namespace_name)
        self.assertEquals(namespace.description, description)


class TestNamespaceModelManager(TestCase):
    namespace_name = 'my_test_ns_2'

    def test_new_namespace_creates_inbound_repo(self):
        """When creating a new Namespace the manager should create inbound instances."""
        self.assertFalse(Namespace.objects.filter(name=self.namespace_name))
        Namespace.objects.create(name=self.namespace_name)
        self.assertTrue(Namespace.objects.filter(name=self.namespace_name).exists())
        inbound_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=self.namespace_name)
        self.assertTrue(AnsibleRepository.objects.filter(name=inbound_name).exists())
        self.assertTrue(AnsibleDistribution.objects.filter(name=inbound_name).exists())

    def test_delete_namespace_deletes_inbound_repo(self):
        """When deleting a Namespace the manager should delete inbound instances."""
        Namespace.objects.get_or_create(name=self.namespace_name)
        ns = Namespace.objects.get(name=self.namespace_name)
        ns.delete()

        inbound_name = INBOUND_REPO_NAME_FORMAT.format(namespace_name=self.namespace_name)

        self.assertFalse(Namespace.objects.filter(name=self.namespace_name).exists())

        self.assertFalse(AnsibleRepository.objects.filter(name=inbound_name).exists())
        self.assertFalse(AnsibleDistribution.objects.filter(name=inbound_name).exists())
