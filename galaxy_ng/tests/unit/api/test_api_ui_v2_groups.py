import logging
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient

from galaxy_ng.app.models import auth as auth_models
from .base import BaseTestCase

log = logging.getLogger(__name__)


class MockSettings:
    """A dictionary like shim that serves as a dynaconf provided settings mock."""
    def __init__(self, kwargs):
        self.kwargs = kwargs
        # every setting should be evaluatable as a property ...
        for k, v in self.kwargs.items():
            setattr(self, k, v)

    def get(self, key, default=None):
        return self.kwargs.get(key, default)


class TestUiV2GroupViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.regular_user = auth_models.User.objects.create(username="regular", is_superuser=False)
        self.group_url = "/api/galaxy/_ui/v2/groups/"

    def test_group_create_success_when_not_connected_to_resource_server(self):
        """Test that groups can be created when not connected to resource server"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        group_data = {"name": "test_group"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.group_url, group_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "test_group")
        self.assertTrue("id" in response.data)

    def test_group_create_blocked_when_connected_to_resource_server(self):
        """Test that group creation is blocked when connected to resource server"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        group_data = {"name": "test_group"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.group_url, group_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_group_update_success_when_not_connected_to_resource_server(self):
        """Test that groups can be updated when not connected to resource server"""
        # First create a group
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"name": "updated_group"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.patch(f"{self.group_url}{group.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "updated_group")

    def test_group_update_blocked_when_connected_to_resource_server(self):
        """Test that group update is blocked when connected to resource server"""
        # First create a group
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"name": "updated_group"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.patch(f"{self.group_url}{group.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_group_put_update_blocked_when_connected_to_resource_server(self):
        """Test that group PUT update is blocked when connected to resource server"""
        # First create a group
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"name": "updated_group"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.put(f"{self.group_url}{group.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_group_delete_success_when_not_connected_to_resource_server(self):
        """Test that groups can be deleted when not connected to resource server"""
        # First create a group
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.delete(f"{self.group_url}{group.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_group_delete_blocked_when_connected_to_resource_server(self):
        """Test that group deletion is blocked when connected to resource server"""
        # First create a group
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.delete(f"{self.group_url}{group.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_group_list_allowed_when_connected_to_resource_server(self):
        """Test that group listing is allowed when connected to resource server"""
        # Create some groups
        auth_models.Group.objects.create(name="test_group1")
        auth_models.Group.objects.create(name="test_group2")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(self.group_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("results" in response.data)

    def test_group_retrieve_allowed_when_connected_to_resource_server(self):
        """Test that group retrieval is allowed when connected to resource server"""
        # Create a group
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(f"{self.group_url}{group.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "test_group")

    def test_group_operations_permission_check(self):
        """Test that proper permissions are enforced for group operations"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}

        # Test with regular user (not superuser)
        self.client.force_authenticate(user=self.regular_user)

        group_data = {"name": "test_group"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Regular user should not be able to create groups
            response = self.client.post(self.group_url, group_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # But should be able to list groups (read-only)
            response = self.client.get(self.group_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_group_filtering_works_with_resource_server(self):
        """Test that filtering still works when connected to resource server"""
        # Create some groups
        auth_models.Group.objects.create(name="test_group1")
        auth_models.Group.objects.create(name="another_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Filter by name
            response = self.client.get(f"{self.group_url}?name=test_group1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "test_group1")

    def test_group_serializer_fields(self):
        """Test that group serializer returns expected fields"""
        group = auth_models.Group.objects.create(name="test_group")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(f"{self.group_url}{group.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_fields = {"id", "name"}
        self.assertEqual(set(response.data.keys()), expected_fields)
        self.assertEqual(response.data["name"], "test_group")
        self.assertEqual(response.data["id"], group.id)
