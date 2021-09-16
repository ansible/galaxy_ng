from galaxy_ng.app.constants import INBOUND_REPO_NAME_FORMAT
from django.test import TestCase
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, Collection

from galaxy_ng.app.models import Namespace


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
