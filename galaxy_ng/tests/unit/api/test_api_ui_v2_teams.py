import logging
from unittest import mock
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.models.auth import Group
from galaxy_ng.app.models.organization import Organization, Team
from .base import BaseTestCase, MockSettings

log = logging.getLogger(__name__)


class TestUiV2TeamViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.regular_user = auth_models.User.objects.create(username="regular", is_superuser=False)
        self.team_url = "/api/galaxy/_ui/v2/teams/"

    def test_team_create_success_when_not_connected_to_resource_server(self):
        """Test that teams can be created when not connected to resource server"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        team_data = {"name": "test_team"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.team_url, team_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "test_team")
        self.assertTrue("id" in response.data)

        # Verify the team was created in the database
        team = Team.objects.get(name="test_team")
        self.assertEqual(team.name, "test_team")
        # Verify default organization was created
        self.assertEqual(team.organization.name, "Default")
        # Verify group name follows pattern
        self.assertEqual(team.group.name, "Default::test_team")

    def test_team_create_with_custom_organization(self):
        """Test that teams can be created with a custom organization"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        team_data = {"name": "test_team", "organization": "CustomOrg"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.team_url, team_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "test_team")

        # Verify the team and organization were created
        team = Team.objects.get(name="test_team")
        self.assertEqual(team.organization.name, "CustomOrg")
        self.assertEqual(team.group.name, "CustomOrg::test_team")

    def test_team_create_blocked_when_connected_to_resource_server(self):
        """Test that team creation is blocked when connected to resource server"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        team_data = {"name": "test_team"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.team_url, team_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_team_update_success_when_not_connected_to_resource_server(self):
        """Test that teams can be updated when not connected to resource server"""
        # First create a team
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"name": "updated_team"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.patch(f"{self.team_url}{team.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "updated_team")

    def test_team_update_blocked_when_connected_to_resource_server(self):
        """Test that team update is blocked when connected to resource server"""
        # First create a team
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"name": "updated_team"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.patch(f"{self.team_url}{team.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_team_put_update_blocked_when_connected_to_resource_server(self):
        """Test that team PUT update is blocked when connected to resource server"""
        # First create a team
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        update_data = {"name": "updated_team"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.put(f"{self.team_url}{team.id}/", update_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_team_delete_success_when_not_connected_to_resource_server(self):
        """Test that teams can be deleted when not connected to resource server"""
        # First create a team
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.delete(f"{self.team_url}{team.id}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_team_delete_blocked_when_connected_to_resource_server(self):
        """Test that team deletion is blocked when connected to resource server"""
        # First create a team
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.delete(f"{self.team_url}{team.id}/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Request should be made to '/api/gateway/v1/teams/'",
            response.content.decode()
        )

    def test_team_list_allowed_when_connected_to_resource_server(self):
        """Test that team listing is allowed when connected to resource server"""
        # Create some teams
        organization = Organization.objects.create(name="TestOrg")
        Team.objects.create(name="test_team1", organization=organization)
        Team.objects.create(name="test_team2", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(self.team_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue("results" in response.data)

    def test_team_retrieve_allowed_when_connected_to_resource_server(self):
        """Test that team retrieval is allowed when connected to resource server"""
        # Create a team
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(f"{self.team_url}{team.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "test_team")

    def test_team_operations_permission_check(self):
        """Test that proper permissions are enforced for team operations"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}

        # Test with regular user (not superuser)
        self.client.force_authenticate(user=self.regular_user)

        team_data = {"name": "test_team"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Regular user should not be able to create teams
            response = self.client.post(self.team_url, team_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # But should be able to list teams (read-only)
            response = self.client.get(self.team_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_team_filtering_works_with_resource_server(self):
        """Test that filtering still works when connected to resource server"""
        # Create some teams
        organization = Organization.objects.create(name="TestOrg")
        Team.objects.create(name="test_team1", organization=organization)
        Team.objects.create(name="another_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Filter by name
            response = self.client.get(f"{self.team_url}?name=test_team1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["name"], "test_team1")

    def test_team_filtering_by_name_contains(self):
        """Test that name contains filtering works"""
        # Create some teams
        organization = Organization.objects.create(name="TestOrg")
        Team.objects.create(name="test_team1", organization=organization)
        Team.objects.create(name="test_team2", organization=organization)
        Team.objects.create(name="another_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": True}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            # Filter by name contains
            response = self.client.get(f"{self.team_url}?name__contains=test")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        team_names = [team["name"] for team in response.data["results"]]
        self.assertIn("test_team1", team_names)
        self.assertIn("test_team2", team_names)
        self.assertNotIn("another_team", team_names)

    def test_team_serializer_fields(self):
        """Test that team serializer returns expected fields"""
        organization = Organization.objects.create(name="TestOrg")
        team = Team.objects.create(name="test_team", organization=organization)

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.get(f"{self.team_url}{team.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_fields = {"id", "name", "group", "organization", "resource"}
        self.assertEqual(set(response.data.keys()), expected_fields)
        self.assertEqual(response.data["name"], "test_team")
        self.assertEqual(response.data["id"], team.id)

        # Verify nested serialization
        self.assertEqual(response.data["organization"]["name"], "TestOrg")
        self.assertEqual(response.data["group"]["name"], team.group.name)

    def test_team_group_name_generation(self):
        """Test that team group names are generated correctly"""
        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        # Test with default organization
        team_data1 = {"name": "team1"}
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response1 = self.client.post(self.team_url, team_data1, format="json")

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        team1 = Team.objects.get(name="team1")
        self.assertEqual(team1.group.name, "Default::team1")

        # Test with custom organization
        team_data2 = {"name": "team2", "organization": "CustomOrg"}
        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response2 = self.client.post(self.team_url, team_data2, format="json")

        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        team2 = Team.objects.get(name="team2")
        self.assertEqual(team2.group.name, "CustomOrg::team2")

    def test_team_create_uses_existing_organization(self):
        """Test that team creation uses existing organization if it exists"""
        # Pre-create an organization
        existing_org = Organization.objects.create(name="ExistingOrg")
        org_count_before = Organization.objects.count()

        kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}
        self.client.force_authenticate(user=self.admin_user)

        team_data = {"name": "test_team", "organization": "ExistingOrg"}

        with patch('galaxy_ng.app.api.ui.v2.views.settings', MockSettings(kwargs)):
            response = self.client.post(self.team_url, team_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify no new organization was created
        self.assertEqual(Organization.objects.count(), org_count_before)

        # Verify the team uses the existing organization
        team = Team.objects.get(name="test_team")
        self.assertEqual(team.organization.id, existing_org.id)


@mock.patch('ansible_base.lib.serializers.mixins.get_setting', return_value=True)
class TestUiV2TeamViewSetEnhancedInputValidation(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.team_url = "/api/galaxy/_ui/v2/teams/"
        self.resource_server_kwargs = {"IS_CONNECTED_TO_RESOURCE_SERVER": False}

    def _post_team(self, team_data):
        self.client.force_authenticate(user=self.admin_user)
        settings_mock = MockSettings(self.resource_server_kwargs)
        with patch('galaxy_ng.app.api.ui.v2.views.settings', settings_mock):
            return self.client.post(self.team_url, team_data, format="json")

    def test_create_succeeds_with_default_organization(self, mock_get_setting):
        """Existing Default org must not be rejected by UniqueValidator."""
        Organization.objects.get_or_create(name="Default")
        response = self._post_team({"name": "team_under_default"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        team = Team.objects.get(name="team_under_default")
        self.assertEqual(team.organization.name, "Default")
        self.assertEqual(team.group.name, "Default::team_under_default")

    def test_create_succeeds_with_existing_organization(self, mock_get_setting):
        """Reuse of an existing org name must not fail uniqueness checks."""
        existing_org = Organization.objects.create(name="ExistingOrg")
        org_count_before = Organization.objects.count()

        response = self._post_team({
            "name": "team_under_existing",
            "organization": "ExistingOrg",
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Organization.objects.count(), org_count_before)
        team = Team.objects.get(name="team_under_existing")
        self.assertEqual(team.organization.id, existing_org.id)

    def test_unsafe_team_name_rejected_on_create(self, mock_get_setting):
        response = self._post_team({"name": "<script>alert(1)</script>"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

    def test_unsafe_organization_name_rejected_on_create(self, mock_get_setting):
        """New prohibited organization names must still be rejected."""
        response = self._post_team({
            "name": "safe_team_name",
            "organization": "<script>alert(1)</script>",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("organization", response.data)
        self.assertNotIn("name", response.data)

    def test_invalid_organization_name_error_keyed_under_organization(self, mock_get_setting):
        """Org name validation failures must not look like team-name errors."""
        response = self._post_team({
            "name": "ok",
            "organization": "Bad (Org)",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("organization", response.data)
        self.assertNotIn("name", response.data)

    def test_create_succeeds_under_grandfathered_organization_name(self, mock_get_setting):
        """Existing org with a prohibited name must be treated as unchanged."""
        legacy_name = "<script>alert(1)</script>"
        existing_org = Organization.objects.create(name=legacy_name)
        org_count_before = Organization.objects.count()

        response = self._post_team({
            "name": "team_under_legacy_org",
            "organization": legacy_name,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Organization.objects.count(), org_count_before)
        team = Team.objects.get(name="team_under_legacy_org")
        self.assertEqual(team.organization.id, existing_org.id)
        self.assertEqual(team.organization.name, legacy_name)

    def test_failed_validation_creates_no_organization_team_or_group(self, mock_get_setting):
        org_count = Organization.objects.count()
        team_count = Team.objects.count()
        group_count = Group.objects.count()

        response = self._post_team({
            "name": "<script>alert(1)</script>",
            "organization": "BrandNewOrg",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(Organization.objects.count(), org_count)
        self.assertEqual(Team.objects.count(), team_count)
        self.assertEqual(Group.objects.count(), group_count)
        self.assertFalse(Organization.objects.filter(name="BrandNewOrg").exists())

        response = self._post_team({
            "name": "another_safe_team",
            "organization": "<script>alert(1)</script>",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(Organization.objects.count(), org_count)
        self.assertEqual(Team.objects.count(), team_count)
        self.assertEqual(Group.objects.count(), group_count)

    def test_duplicate_team_name_rejected_on_create(self, mock_get_setting):
        team_data = {"name": "duplicate_team_name", "organization": "DupOrg"}
        response = self._post_team(team_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

        response = self._post_team(team_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertIn("already exists", str(response.data).lower())
        self.assertEqual(Team.objects.filter(name="duplicate_team_name").count(), 1)
        self.assertEqual(Organization.objects.filter(name="DupOrg").count(), 1)

    def test_duplicate_team_does_not_leave_new_organization(self, mock_get_setting):
        """Duplicate rejection must not persist a newly created organization."""
        Organization.objects.create(name="FirstOrg")
        Team.objects.create(
            name="shared_team_name",
            organization=Organization.objects.get(name="FirstOrg"),
        )
        org_count = Organization.objects.count()

        response = self._post_team({
            "name": "shared_team_name",
            "organization": "OrphanOrg",
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
        self.assertEqual(Team.objects.filter(name="shared_team_name").count(), 1)
        self.assertEqual(Organization.objects.count(), org_count)
        self.assertFalse(Organization.objects.filter(name="OrphanOrg").exists())
