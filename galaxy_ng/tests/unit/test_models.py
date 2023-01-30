from django.test import TestCase
from pulp_ansible.app.models import AnsibleRepository, Collection

from galaxy_ng.app.models import Namespace


class TestSignalCreateRepository(TestCase):
    def test_create_repository_ensure_retain_repo_versions(self):
        """On creation retain_repo_versions is set to 1 if omited"""
        repo_name = "test"
        repository = AnsibleRepository.objects.create(name=repo_name)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 1)

    def test_when_set_not_changed_retain_repo_versions(self):
        """On creation retain_repo_versions is not changed when explicit set"""
        repo_name = "test2"
        repository = AnsibleRepository.objects.create(name=repo_name, retain_repo_versions=99)
        self.assertEqual(repository.name, repo_name)
        self.assertEqual(repository.retain_repo_versions, 99)

    def test_update_do_not_change_retain_repo_versions(self):
        """On update retain_repo_versions is not changed when already exists"""
        # Create repo setting retain_repo_versions
        repo_name = "test3"
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
