import string
import random

from pulpcore.client.galaxy_ng.exceptions import ApiException
from galaxy_ng.tests.functional.utils import TestCaseUsingBindings
from galaxy_ng.tests.functional.utils import set_up_module as setUpModule  # noqa:F401


class CreateNamespaceTestCase(TestCaseUsingBindings):
    """Test whether a namespace can be created."""

    def delete_namespace(self, namespace_name):
        # delete namespace
        # namespace_api does not support delete, so we can use the smash_client directly
        response = self.smash_client.delete(
            f"{self.galaxy_api_prefix}/v3/namespaces/{namespace_name}"
        )
        self.assertEqual(response.status_code, 204)

    def test_create_and_delete_namespace(self):
        # generate name formed by 10 random ascii lowercase letters
        random_name = ''.join(random.choices(string.ascii_lowercase, k=10))
        namespace_data = {"name": random_name, "groups": []}

        # create namespace
        namespace = self.namespace_api.create(namespace=namespace_data)
        self.assertEqual(namespace.name, random_name)

        # ensure namespace is available
        namespaces = self.namespace_api.list(limit=100)
        self.assertIn(namespace.name, [item.name for item in namespaces.data])

        # delete namespace
        self.delete_namespace(namespace.name)

        # ensure namespace is NO MORE available
        namespaces = self.namespace_api.list(limit=100)
        self.assertNotIn(namespace.name, [item.name for item in namespaces.data])

    def test_negative_create_namespace_with_invalid_name(self):
        # generate name formed by 10 random ascii lowercase letters
        random_name = ''.join(random.choices(string.ascii_lowercase, k=10))
        random_name = f"ABC-{random_name}-$@"
        namespace_data = {"name": random_name, "groups": []}

        # expect the namespace is not created because of invalid name
        with self.assertRaises(ApiException) as context:
            self.namespace_api.create(namespace=namespace_data)

        # Bad request
        assert context.exception.status == 400
