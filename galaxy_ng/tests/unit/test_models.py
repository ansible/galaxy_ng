from django.test import TestCase
from pulp_ansible.app.models import Collection

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
