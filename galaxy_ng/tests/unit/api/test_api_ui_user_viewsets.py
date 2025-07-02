import logging
import pytest

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.access_control.statements.roles import LOCKED_ROLES
from .base import BaseTestCase, get_current_ui_url

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


class TestUiV2UserViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()
        self.user_url = "/api/galaxy/_ui/v2/users/"

    def test_user_create_blocked_when_connected_to_resource_server(self):
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        new_user_data = {
            "username": "haxor_test3",
            "password": "cantTouchThis123",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, new_user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/users/'",
            response.content.decode()
        )

    def test_user_create_success_when_not_connected_to_resource_server(self):
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        new_user_data = {
            "username": "haxor_test3",
            "password": "cantTouchThis123",
            "email": "test@example.com",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, new_user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "haxor_test3")
        self.assertEqual(response.data["email"], "test@example.com")
        self.assertTrue("id" in response.data)

    def test_user_update_blocked_when_connected_to_resource_server(self):
        """Test that user update is blocked when connected to resource server"""
        # First create a user
        user = auth_models.User.objects.create(
            username="test_user",
            email="original@example.com"
        )
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"email": "updated@example.com"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.patch(f"{self.user_url}{user.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/users/'",
            response.content.decode()
        )

    def test_user_update_success_when_not_connected_to_resource_server(self):
        """Test that user update works when not connected to resource server"""
        # First create a user
        user = auth_models.User.objects.create(
            username="test_user",
            email="original@example.com"
        )
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"email": "updated@example.com", "username": "test_user"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.patch(f"{self.user_url}{user.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "updated@example.com")
        self.assertEqual(response.data["username"], "test_user")

    def test_user_put_update_blocked_when_connected_to_resource_server(self):
        """Test that user PUT update is blocked when connected to resource server"""
        # First create a user
        user = auth_models.User.objects.create(
            username="test_user",
            email="original@example.com"
        )
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {
            "username": "test_user",
            "email": "updated@example.com",
            "first_name": "Test",
            "last_name": "User"
        }

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.put(f"{self.user_url}{user.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/users/'",
            response.content.decode()
        )

    def test_user_delete_blocked_when_connected_to_resource_server(self):
        """Test that user deletion is blocked when connected to resource server"""
        # First create a user
        user = auth_models.User.objects.create(username="test_user")
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.delete(f"{self.user_url}{user.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/users/'",
            response.content.decode()
        )

    def test_user_delete_success_when_not_connected_to_resource_server(self):
        """Test that user deletion works when not connected to resource server"""
        # First create a user
        user = auth_models.User.objects.create(username="test_user")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.delete(f"{self.user_url}{user.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_list_allowed_when_connected_to_resource_server(self):
        """Test that user listing is allowed when connected to resource server"""
        # Create some users
        auth_models.User.objects.create(username="test_user1")
        auth_models.User.objects.create(username="test_user2")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(self.user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("results" in response.data)

    def test_user_retrieve_allowed_when_connected_to_resource_server(self):
        """Test that user retrieval is allowed when connected to resource server"""
        # Create a user
        user = auth_models.User.objects.create(
            username="test_user",
            email="test@example.com"
        )

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(f"{self.user_url}{user.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "test_user")
        self.assertEqual(response.data["email"], "test@example.com")

    def test_user_serializer_fields_for_list_retrieve(self):
        """Test that user detail serializer returns expected fields for list/retrieve"""
        user = auth_models.User.objects.create(
            username="test_user",
            email="test@example.com",
            first_name="Test",
            last_name="User"
        )

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(f"{self.user_url}{user.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_fields = {
            "id", "username", "first_name", "last_name", "email",
            "groups", "teams", "organizations", "date_joined", "is_superuser", "resource"
        }
        self.assertEqual(set(response.data.keys()), expected_fields)

    def test_user_filtering_works_with_resource_server(self):
        """Test that filtering still works when connected to resource server"""
        # Create some users
        auth_models.User.objects.create(username="test_user1", email="test1@example.com")
        auth_models.User.objects.create(username="another_user", email="test2@example.com")

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Filter by username
            response = self.client.get(f"{self.user_url}?username=test_user1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["username"], "test_user1")

    def test_user_ordering_by_id(self):
        """Test that users are ordered by ID"""
        # Create test users
        users = []
        for i in range(3):
            user = auth_models.User.objects.create(
                username=f"test_user_{i}",
                email=f"test{i}@example.com"
            )
            users.append(user)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(self.user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Extract our test users from the results
        test_users = [u for u in response.data["results"] if u["username"].startswith("test_user_")]

        # Verify ordering by ID (ascending)
        user_ids = [u["id"] for u in test_users]
        self.assertEqual(user_ids, sorted(user_ids))

    def test_user_pagination(self):
        """Test pagination of users"""
        # Create multiple test users
        created_users = []
        for i in range(3):
            user = auth_models.User.objects.create(
                username=f"paginate_user_{i}",
                email=f"paginate{i}@example.com"
            )
            created_users.append(user)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Test pagination with page_size=2
            response = self.client.get(f"{self.user_url}?page_size=2")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("results" in response.data)
        self.assertTrue("next" in response.data)
        self.assertTrue("previous" in response.data)

    def test_user_validation_errors(self):
        """Test that proper validation errors are returned"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        # Test empty username
        user_data = {"username": "", "email": "test@example.com"}
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test missing username
        user_data = {"email": "test@example.com"}
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Test duplicate username
        auth_models.User.objects.create(username="existing_user")
        user_data = {"username": "existing_user", "email": "test@example.com"}
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_password_handling(self):
        """Test password handling in user creation and updates"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        # Test user creation with password
        user_data = {
            "username": "password_user",
            "email": "password@example.com",
            "password": "secure_password123"
        }
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Password should not be returned in response
        self.assertNotIn("password", response.data)

        # Verify user can login with the password
        created_user = auth_models.User.objects.get(username="password_user")
        self.assertTrue(created_user.check_password("secure_password123"))

    def test_user_groups_validation(self):
        """Test validation of groups field in user data"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        # Test with valid group
        user_data = {
            "username": "group_test_user",
            "email": "group@example.com",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}]
        }
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Test with non-existent group
        user_data = {
            "username": "invalid_group_user",
            "email": "invalid@example.com",
            "groups": [{"id": 99999, "name": "non_existent_group"}]
        }
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.user_url, user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_non_existent_user_error(self):
        """Test that accessing a non-existent user raises a 404 error"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Try to retrieve a non-existent user
            response = self.client.get(f"{self.user_url}999999/")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # Try to update a non-existent user
            response = self.client.patch(
                f"{self.user_url}999999/",
                {"email": "test@example.com"},
                format="json"
            )
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

            # Try to delete a non-existent user
            response = self.client.delete(f"{self.user_url}999999/")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestUiUserViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.user_url = get_current_ui_url("users-list")
        self.me_url = get_current_ui_url("me")

    @override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
    def test_super_user(self):
        user = auth_models.User.objects.create(username="haxor")
        self._create_group(
            "",
            "test_group1",
            users=[user],
            roles=[
                "galaxy.user_admin",
            ],
        )
        self.client.force_authenticate(user=user)
        new_user_data = {
            "username": "haxor_test1",
            "password": "cantTouchThis123",
            "groups": [],
            "is_superuser": True,
        }

        # test that regular user's can't create super users
        response = self.client.post(self.user_url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test that admins can create super users
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.user_url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        my_data = {
            "username": user.username,
            "password": "cantTouchThis123",
            "groups": [],
            "is_superuser": True,
        }

        # Test that user's can't elevate their perms
        self.client.force_authenticate(user=user)
        response = self.client.put(self.me_url, my_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        put_url = "{}{}/".format(self.user_url, user.id)
        response = self.client.put(put_url, my_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # test that the admin can update another user
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(put_url, my_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
    def test_user_can_only_create_users_with_their_groups(self):
        user = auth_models.User.objects.create(username="haxor")
        group = self._create_group(
            "",
            "test_group1",
            users=[user],
            roles=[
                "galaxy.user_admin",
            ],
        )
        self.client.force_authenticate(user=user)

        # Verify the user can't create new users with elevated permissions
        new_user_data = {
            "username": "haxor_test1",
            "password": "cantTouchThis123",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        response = self.client.post(self.user_url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["errors"][0]["source"]["parameter"], "groups")

        # Verify the user can create new users with identical permissions
        new_user_data = {
            "username": "haxor_test2",
            "password": "cantTouchThis123",
            "groups": [{"id": group.id, "name": group.name}],
        }

        response = self.client.post(self.user_url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
    def test_user_can_create_users_with_right_perms(self):
        user = auth_models.User.objects.create(username="haxor")
        self._create_group(
            "",
            "test_group1",
            users=[user],
            roles=[
                "galaxy.user_admin",
                "galaxy.group_admin",
            ],
        )
        self.client.force_authenticate(user=user)

        new_user_data = {
            "username": "haxor_test3",
            "password": "cantTouchThis123",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        response = self.client.post(self.user_url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def _test_user_list(self, expected=None):
        # Check test user can[not] view other users
        self.client.force_authenticate(user=self.user)
        log.debug("self.client: %s", self.client)
        log.debug("self.client.__dict__: %s", self.client.__dict__)
        response = self.client.get(self.user_url)
        self.assertEqual(response.status_code, expected)

        # Check admin user can -always- view others
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.user_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data["data"]
        self.assertEqual(len(data), auth_models.User.objects.all().count())

    def test_user_list_standalone(self):
        kwargs = {
            'GALAXY_DEPLOYMENT_MODE': DeploymentMode.STANDALONE.value,
        }
        with patch('galaxy_ng.app.access_control.access_policy.settings', MockSettings(kwargs)):
            self._test_user_list(expected=status.HTTP_403_FORBIDDEN)

    def test_user_list_insights(self):
        kwargs = {
            'GALAXY_DEPLOYMENT_MODE': DeploymentMode.INSIGHTS.value,
            'RH_ENTITLEMENT_REQUIRED': 'insights',
        }
        with patch('galaxy_ng.app.access_control.access_policy.settings', MockSettings(kwargs)):
            self._test_user_list(expected=status.HTTP_403_FORBIDDEN)

    def test_user_list_community(self):
        kwargs = {
            'GALAXY_DEPLOYMENT_MODE': DeploymentMode.STANDALONE.value,
            'SOCIAL_AUTH_GITHUB_KEY': '1234',
            'SOCIAL_AUTH_GITHUB_SECRET': '1234'
        }
        with patch('galaxy_ng.app.access_control.access_policy.settings', MockSettings(kwargs)):
            self._test_user_list(expected=status.HTTP_200_OK)

    def test_user_get(self):
        def _test_user_get(expected=None):
            # Check test user can[not] view themselves on the users/ api
            self.client.force_authenticate(user=self.user)
            url = "{}{}/".format(self.user_url, self.user.id)

            response = self.client.get(url)
            self.assertEqual(response.status_code, expected)

            # Check test user can[not] view other users
            url = "{}{}/".format(self.user_url, self.admin_user.id)
            response = self.client.get(url)
            self.assertEqual(response.status_code, expected)

            # Check admin user can -always- view others
            self.client.force_authenticate(user=self.admin_user)
            url = "{}{}/".format(self.user_url, self.user.id)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data
            self.assertEqual(data["email"], self.user.email)
            self.assertEqual(data["first_name"], self.user.first_name)
            self.assertEqual(len(data["groups"]), self.user.groups.all().count())
            for group in data["groups"]:
                self.assertTrue(self.user.groups.exists(id=group["id"]))

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            _test_user_get(expected=status.HTTP_403_FORBIDDEN)

        # FIXME(jtanner): not sure why broken
        '''
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            _test_user_get(expected=status.HTTP_403_FORBIDDEN)
        '''

        # FIXME(jtanner): broken by dab 2024.12.13
        '''
        # community
        kwargs = {
            'GALAXY_DEPLOYMENT_MODE': DeploymentMode.STANDALONE.value,
            'SOCIAL_AUTH_GITHUB_KEY': '1234',
            'SOCIAL_AUTH_GITHUB_SECRET': '1234'
        }
        with self.settings(**kwargs):
            _test_user_get(expected=status.HTTP_200_OK)
        '''

    def _test_create_or_update(self, method_call, url, new_user_data, crud_status, auth_user):
        self.client.force_authenticate(user=auth_user)
        # set user with invalid password
        new_user_data["password"] = "12345678"
        response = method_call(url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_messages = set()
        for err in response.data["errors"]:
            error_messages.add(err["code"])

        desired_errors = {"password_too_short", "password_too_common", "password_entirely_numeric"}

        self.assertEqual(error_messages, desired_errors)

        # set valid user
        new_user_data["password"] = "trekkie4Lyfe1701"
        response = method_call(url, new_user_data, format="json")
        self.assertEqual(response.status_code, crud_status)
        data = response.data
        self.assertEqual(data["email"], new_user_data["email"])
        self.assertEqual(data["first_name"], new_user_data["first_name"])
        self.assertEqual(data["groups"], new_user_data["groups"])
        self.assertFalse(self.client.login(username=new_user_data["username"], password="bad"))
        self.assertTrue(
            self.client.login(
                username=new_user_data["username"], password=new_user_data["password"]
            )
        )

        return response

    def test_user_create(self):
        new_user_data = {
            "username": "test2",
            "first_name": "First",
            "last_name": "Last",
            "email": "email@email.com",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        '''
        # user create disabled in insights mode
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.post(self.user_url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        '''

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            # test user cannot create
            self.client.force_authenticate(user=self.user)
            response = self.client.post(self.user_url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # admin can create
            self._test_create_or_update(
                self.client.post,
                self.user_url,
                new_user_data,
                status.HTTP_201_CREATED,
                self.admin_user,
            )

    def test_user_update(self):
        user = auth_models.User.objects.create(username="test2")
        put_url = "{}{}/".format(self.user_url, user.id)
        user.groups.add(self.pe_group)
        user.save()
        new_user_data = {
            "username": "test2",
            "first_name": "First",
            "last_name": "Last",
            "email": "email@email.com",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        '''
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self._test_create_or_update(
                self.client.put, put_url, new_user_data, status.HTTP_200_OK, self.admin_user
            )
        '''

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            # test user cannot edit
            self.client.force_authenticate(user=self.user)
            response = self.client.put(put_url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # admin can edit
            self._test_create_or_update(
                self.client.put, put_url, new_user_data, status.HTTP_200_OK, self.admin_user
            )

    def test_me_get(self):
        self.client.force_authenticate(user=self.user)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            response = self.client.get(self.me_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["username"], self.user.username)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.get(self.me_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["username"], self.user.username)

    def test_me_update(self):
        user = auth_models.User.objects.create(username="me_test")
        user.save()
        new_user_data = {
            "username": "test2",
            "first_name": "First",
            "last_name": "Last",
            "email": "email@email.com",
            "groups": [],
        }

        self._test_create_or_update(
            self.client.put, self.me_url, new_user_data, status.HTTP_200_OK, user
        )

        new_user_data = {
            "username": "test2",
            "first_name": "First",
            "last_name": "Last",
            "email": "email@email.com",
            "groups": [{"id": self.pe_group.id, "name": self.pe_group.name}],
        }

        url = "{}{}/".format(self.user_url, user.id)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            response = self.client.put(url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=self.admin_user)
            response = self.client.put(url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self.client.force_authenticate(user=self.user)
            response = self.client.put(url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=self.admin_user)
            response = self.client.put(url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_me_delete(self):
        user = auth_models.User.objects.create(username="delete_me_test")
        user.save()

        group = self._create_group(
            "",
            "people_that_can_delete_users",
            users=[user],
            roles=["galaxy.user_admin", "galaxy.group_admin"],
        )
        self.client.force_authenticate(user=user)

        new_user_data = {
            "username": "delete_me_test",
            "first_name": "Del",
            "last_name": "Eetmi",
            "email": "email@email.com",
            "groups": [{"id": group.id, "name": group.name}],
        }

        url = "{}{}/".format(self.user_url, user.id)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            self._test_create_or_update(
                self.client.put, self.me_url, new_user_data, status.HTTP_200_OK, user
            )

            client = APIClient(raise_request_exception=True)
            client.force_authenticate(user=user)

            response = client.delete(url, format="json")

            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # should only be one 403 error for this case
            error = response.data["errors"][0]

            self.assertEqual(error["status"], "403")
            self.assertEqual(error["code"], "permission_denied")

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self.client.force_authenticate(user=self.admin_user)
            response = client.delete(url, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @pytest.mark.skip(reason="FIXME(jtanner): broken by dab-rbac")
    def test_me_content_admin_permissions(self):
        user = auth_models.User.objects.create(username="content_admin_user")
        user.save()

        group = self._create_group(
            "",
            "users_with_content_admin_permissions",
            users=[user],
            roles=["galaxy.content_admin"],
        )
        self.client.force_authenticate(user=user)

        new_user_data = {
            "username": "content_admin_user",
            "first_name": "Tsrif",
            "last_name": "Tsal",
            "email": "email@email.com",
            "groups": [{"id": group.id, "name": group.name}],
        }

        excluded_model_permissions = [
            "core.change_task",
            "core.delete_task",
            "core.view_task",
            "galaxy.view_user",
            "galaxy.change_group",
            "galaxy.view_group",
            "galaxy.delete_user",
            "galaxy.change_user",
            "galaxy.add_user",
            "galaxy.add_group",
            "galaxy.delete_group"]

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            self._test_create_or_update(self.client.put, self.me_url,
                                        new_user_data, status.HTTP_200_OK, user)
            client = APIClient(raise_request_exception=True)
            client.force_authenticate(user=user)
            response = self.client.get(self.me_url)
            content_admin_permissions = LOCKED_ROLES["galaxy.content_admin"]["permissions"]
            my_permissions = response.data["model_permissions"]
            for permission in my_permissions:
                self.assertEqual(my_permissions[permission]
                                 ["has_model_permission"], permission in content_admin_permissions)

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self.client.force_authenticate(user=user)
            response = self.client.get(self.me_url)
            content_admin_permissions = LOCKED_ROLES["galaxy.content_admin"]["permissions"]
            for i in content_admin_permissions:
                self.assertTrue(response.data["model_permissions"][i]["has_model_permission"])
            for i in excluded_model_permissions:
                self.assertFalse(response.data["model_permissions"][i]["has_model_permission"])

    @override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
    def test_superuser_can_not_be_deleted(self):
        superuser = auth_models.User.objects.create(
            username="super_delete_me_test", is_superuser=True
        )
        superuser.save()

        user = auth_models.User.objects.create(username="user_trying_to_delete_superuser")
        user.save()

        group = self._create_group(
            "",
            "people_that_can_delete_users",
            users=[user],
            roles=["galaxy.user_admin", "galaxy.group_admin"],
        )

        new_user_data = {
            "username": "user_trying_to_delete_superuser",
            "first_name": "Del",
            "last_name": "Sooperuuser",
            "email": "email@email.com",
            "groups": [{"id": group.id, "name": group.name}],
        }

        self._test_create_or_update(
            self.client.put, self.me_url, new_user_data, status.HTTP_200_OK, user
        )

        # try to delete a user that is_super_user
        url = "{}{}/".format(self.user_url, superuser.id)

        client = APIClient(raise_request_exception=True)
        client.force_authenticate(user=user)

        response = client.delete(url, format="json")

        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Try to delete 'admin' user
        url = "{}{}/".format(self.user_url, self.admin_user.id)
        response = client.delete(url, format="json")

        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
