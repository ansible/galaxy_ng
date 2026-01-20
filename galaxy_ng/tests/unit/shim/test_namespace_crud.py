import django_guid
import logging
import pytest
import uuid

from django.test import TestCase, RequestFactory
from pulp_ansible.app.models import Collection
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from galaxy_ng.app import models
from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.shim.namespace.functions.pulp_namespace import (
    create_namespace,
    retrieve_namespace,
    update_namespace,
    delete_namespace,
    list_namespaces,
)
from galaxy_ng.app.exceptions import ConflictError

log = logging.getLogger(__name__)


@pytest.mark.parametrize(('invalid_name', 'reason'), [
    ('ab', 'too short'),
    ('TestNamespace', 'contains uppercase'),
    ('_testnamespace', 'starts with underscore'),
    ('test-namespace', 'contains invalid character'),
])
@pytest.mark.django_db
def test_create_namespace_invalid_name(invalid_name, reason):
    """Test that invalid namespace names raise ValidationError."""
    with pytest.raises(ValidationError):
        create_namespace(name=invalid_name, request=None)


class TestNamespaceCRUDFunctions(TestCase):
    """Unit tests for standalone namespace CRUD functions."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Set GUID for task dispatching (required by PulpCore)
        django_guid.set_guid(django_guid.utils.generate_guid())

        self.admin_user = auth_models.User.objects.create(username='admin')
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        # Create a request factory and mock request for serializers
        self.factory = RequestFactory()
        http_request = self.factory.get('/')
        self.request = Request(http_request)
        self.request.user = self.admin_user

        # Common test data
        self.company = 'Test Company'
        self.email = 'test@example.com'
        self.description = 'A test namespace'

    @staticmethod
    def _create_partner_engineer_group():
        """Create a partner engineer group for testing."""
        group, _ = auth_models.Group.objects.get_or_create_identity(
            'partner-engineers',
            'partner_engineers'
        )
        return group

    def _unique_name(self, base='ns'):
        """Generate a unique namespace name."""
        return f"{base}_{uuid.uuid4().hex[:8]}"

    def test_create_namespace(self):
        """Test creating a namespace with valid data."""
        ns_name = self._unique_name('testnamespace')
        response = create_namespace(
            name=ns_name,
            company=self.company,
            email=self.email,
            description=self.description,
            request=self.request
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], ns_name)
        self.assertEqual(response.data['company'], self.company)
        self.assertEqual(response.data['email'], self.email)
        self.assertEqual(response.data['description'], self.description)

        # Verify it was created in the database
        namespace = models.Namespace.objects.get(name=ns_name)
        self.assertEqual(namespace.company, self.company)

    def test_create_namespace_duplicate_raises_conflict(self):
        """Test that creating a duplicate namespace raises ConflictError."""
        ns_name = self._unique_name('duplicate')
        create_namespace(name=ns_name, request=self.request)

        with pytest.raises(ConflictError) as cm:
            create_namespace(name=ns_name, request=self.request)

        self.assertIn('already exists', str(cm.value.detail))

    def test_create_namespace_with_links(self):
        """Test creating a namespace with links."""
        ns_name = self._unique_name('testnamespace')
        response = create_namespace(
            name=ns_name,
            links=[
                {'name': 'Homepage', 'url': 'https://example.com'},
                {'name': 'Documentation', 'url': 'https://docs.example.com'}
            ],
            request=self.request
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['links']), 2)

        namespace = models.Namespace.objects.get(name=ns_name)
        self.assertEqual(namespace.links.count(), 2)

    def test_retrieve_namespace(self):
        """Test retrieving a namespace by name."""
        ns_name = self._unique_name('testnamespace')
        create_namespace(
            name=ns_name,
            company=self.company,
            email=self.email,
            request=self.request
        )

        response = retrieve_namespace(ns_name, request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], ns_name)
        self.assertEqual(response.data['company'], self.company)

    def test_retrieve_namespace_not_found(self):
        """Test retrieving a non-existent namespace raises ValidationError."""
        with pytest.raises(ValidationError) as cm:
            retrieve_namespace('nonexistent', request=self.request)

        self.assertIn('does not exist', str(cm.value.detail))

    def test_update_namespace(self):
        """Test updating a namespace."""
        ns_name = self._unique_name('testnamespace')
        create_namespace(
            name=ns_name,
            company='Old Company',
            email='old@example.com',
            request=self.request
        )

        response = update_namespace(
            ns_name,
            company='New Company',
            email='new@example.com',
            request=self.request
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company'], 'New Company')
        self.assertEqual(response.data['email'], 'new@example.com')

        # Verify in database
        namespace = models.Namespace.objects.get(name=ns_name)
        self.assertEqual(namespace.company, 'New Company')
        self.assertEqual(namespace.email, 'new@example.com')

    def test_update_namespace_partial(self):
        """Test partial update of a namespace."""
        ns_name = self._unique_name('testnamespace')
        create_namespace(
            name=ns_name,
            company=self.company,
            email=self.email,
            description='Original description',
            request=self.request
        )

        response = update_namespace(
            ns_name,
            description='Updated description',
            request=self.request
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated description')
        # Other fields should remain unchanged
        self.assertEqual(response.data['company'], self.company)
        self.assertEqual(response.data['email'], self.email)

    def test_update_namespace_not_found(self):
        """Test updating a non-existent namespace raises ValidationError."""
        with pytest.raises(ValidationError) as cm:
            update_namespace('nonexistent', company='New Company', request=self.request)

        self.assertIn('does not exist', str(cm.value.detail))

    def test_update_namespace_links(self):
        """Test updating namespace links."""
        ns_name = self._unique_name('testnamespace')
        create_namespace(
            name=ns_name,
            links=[
                {'name': 'Homepage', 'url': 'https://example.com'}
            ],
            request=self.request
        )

        response = update_namespace(
            ns_name,
            links=[
                {'name': 'Homepage', 'url': 'https://newexample.com'},
                {'name': 'Docs', 'url': 'https://docs.example.com'}
            ],
            request=self.request
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['links']), 2)

    def test_delete_namespace(self):
        """Test deleting a namespace."""
        ns_name = self._unique_name('testnamespace')
        create_namespace(name=ns_name, request=self.request)

        response = delete_namespace(ns_name)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify it was deleted from the database
        self.assertEqual(
            models.Namespace.objects.filter(name=ns_name).count(),
            0
        )

    def test_delete_namespace_not_found(self):
        """Test deleting a non-existent namespace raises ValidationError."""
        with pytest.raises(ValidationError) as cm:
            delete_namespace('nonexistent')

        self.assertIn('does not exist', str(cm.value.detail))

    def test_delete_namespace_with_collections(self):
        """Test that deleting a namespace with collections raises error."""
        ns_name = self._unique_name('testnamespace')
        create_namespace(name=ns_name, request=self.request)

        # Create a collection in the namespace
        # Note: This requires proper Collection model setup
        Collection.objects.create(namespace=ns_name, name='testcoll')

        with pytest.raises(ValidationError) as cm:
            delete_namespace(ns_name)

        self.assertIn('cannot be deleted', str(cm.value.detail))
        self.assertIn('collections associated', str(cm.value.detail))

        # Verify namespace was not deleted
        self.assertEqual(
            models.Namespace.objects.filter(name=ns_name).count(),
            1
        )

    def test_list_namespaces_empty(self):
        """Test listing namespaces when none exist."""
        # Don't create any namespaces
        response = list_namespaces(request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # May have namespaces from other tests, just check it works
        self.assertIsInstance(response.data, list)

    def test_list_namespaces(self):
        """Test listing multiple namespaces."""
        ns1 = self._unique_name('namespace1')
        ns2 = self._unique_name('namespace2')
        ns3 = self._unique_name('namespace3')

        create_namespace(name=ns1, company='Company A', request=self.request)
        create_namespace(name=ns2, company='Company B', request=self.request)
        create_namespace(name=ns3, company='Company C', request=self.request)

        response = list_namespaces(request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 3)

        names = [ns['name'] for ns in response.data]
        self.assertIn(ns1, names)
        self.assertIn(ns2, names)
        self.assertIn(ns3, names)

    def test_list_namespaces_filter_by_name(self):
        """Test filtering namespaces by exact name."""
        ns1 = self._unique_name('namespace1')
        ns2 = self._unique_name('namespace2')

        create_namespace(name=ns1, request=self.request)
        create_namespace(name=ns2, request=self.request)

        response = list_namespaces(name=ns1, request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ns1)

    def test_list_namespaces_filter_by_company(self):
        """Test filtering namespaces by company."""
        ns1 = self._unique_name('namespace1')
        ns2 = self._unique_name('namespace2')
        ns3 = self._unique_name('namespace3')

        create_namespace(name=ns1, company='Company A', request=self.request)
        create_namespace(name=ns2, company='Company B', request=self.request)
        create_namespace(name=ns3, company='Company A', request=self.request)

        response = list_namespaces(company='Company A', request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        names = [ns['name'] for ns in response.data]
        self.assertIn(ns1, names)
        self.assertIn(ns3, names)

    def test_list_namespaces_filter_by_keywords(self):
        """Test filtering namespaces by keywords."""
        # Use a unique keyword for this test
        unique_kw = f"testkw{uuid.uuid4().hex[:6]}"
        ns1 = self._unique_name('testnamespace')
        ns2 = self._unique_name('prodnamespace')
        ns3 = self._unique_name('devnamespace')

        create_namespace(
            name=ns1, company=f'{unique_kw} Company', request=self.request
        )
        create_namespace(name=ns2, company='Production Co', request=self.request)
        create_namespace(
            name=ns3, company=f'{unique_kw} Development', request=self.request
        )

        # Search for unique keyword - should match ns1 and ns3
        response = list_namespaces(keywords=[unique_kw], request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        names = [ns['name'] for ns in response.data]
        self.assertIn(ns1, names)
        self.assertIn(ns3, names)

    def test_list_namespaces_filter_by_multiple_keywords(self):
        """Test filtering namespaces by multiple keywords."""
        # Use unique keywords for this test
        kw1 = f"kw1{uuid.uuid4().hex[:6]}"
        kw2 = f"kw2{uuid.uuid4().hex[:6]}"
        ns1 = self._unique_name('testnamespace')
        ns2 = self._unique_name('prodnamespace')

        create_namespace(
            name=ns1, company=f'{kw1} {kw2} Company', request=self.request
        )
        create_namespace(
            name=ns2, company=f'{kw1} Production', request=self.request
        )

        # Both keywords must match (AND operation)
        response = list_namespaces(keywords=[kw1, kw2], request=self.request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only match ns1 which has both keywords
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], ns1)

    def test_create_namespace_minimal_data(self):
        """Test creating a namespace with only required fields."""
        ns_name = self._unique_name('minimal')
        response = create_namespace(name=ns_name, request=self.request)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], ns_name)
        self.assertEqual(response.data['company'], '')
        self.assertEqual(response.data['email'], '')

    def test_namespace_crud_workflow(self):
        """Test complete CRUD workflow for a namespace."""
        ns_name = self._unique_name('workflow')

        # Create
        create_response = create_namespace(
            name=ns_name,
            company='Initial Company',
            request=self.request
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        # Retrieve
        retrieve_response = retrieve_namespace(ns_name, request=self.request)
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.data['company'], 'Initial Company')

        # Update
        update_response = update_namespace(
            ns_name,
            company='Updated Company',
            request=self.request
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['company'], 'Updated Company')

        # List
        list_response = list_namespaces(name=ns_name, request=self.request)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        # Delete
        delete_response = delete_namespace(ns_name)
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify deletion
        self.assertEqual(
            models.Namespace.objects.filter(name=ns_name).count(),
            0
        )
