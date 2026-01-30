import logging
from unittest.mock import patch

from rest_framework import status
from rest_framework.test import APIClient

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.models.organization import Organization, Team
from .base import BaseTestCase

log = logging.getLogger(__name__)


class TestUiV2RBACFiltering(BaseTestCase):
    """Test RBAC filtering for UI v2 endpoints."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.admin_user = auth_models.User.objects.create(username="admin", is_superuser=True)
        self.user1 = auth_models.User.objects.create(username="user1", is_superuser=False)
        self.user2 = auth_models.User.objects.create(username="user2", is_superuser=False)
        self.user3 = auth_models.User.objects.create(username="user3", is_superuser=False)

        # URLs
        self.users_url = "/api/galaxy/_ui/v2/users/"
        self.groups_url = "/api/galaxy/_ui/v2/groups/"
        self.organizations_url = "/api/galaxy/_ui/v2/organizations/"
        self.teams_url = "/api/galaxy/_ui/v2/teams/"

    def _mock_access_qs(self, model_class, user, allowed_ids):
        """Mock the access_qs method to filter objects based on allowed IDs."""
        def access_qs_side_effect(requesting_user, queryset=None):
            if queryset is None:
                queryset = model_class.objects.all()
            if requesting_user.is_superuser:
                return queryset
            return queryset.filter(id__in=allowed_ids)
        return access_qs_side_effect

    def _setup_rbac_mocks(self, model_class, user, allowed_ids):
        """Set up mocks for RBAC filtering."""
        # Mock permission_registry.is_registered to return True
        permission_registry_patch = patch(
            'galaxy_ng.app.api.ui.v2.views.permission_registry.is_registered',
            return_value=True
        )
        permission_registry_patch.start()
        self.addCleanup(permission_registry_patch.stop)

        # Mock the access_qs method - create it if it doesn't exist
        access_qs_patch = patch.object(
            model_class,
            'access_qs',
            create=True,
            side_effect=self._mock_access_qs(model_class, user, allowed_ids)
        )
        access_qs_patch.start()
        self.addCleanup(access_qs_patch.stop)

    def test_user_list_filtered_by_rbac(self):
        """Test that user listing is filtered based on RBAC permissions."""
        # Create additional users
        user4 = auth_models.User.objects.create(username="user4", is_superuser=False)
        user5 = auth_models.User.objects.create(username="user5", is_superuser=False)

        # user1 should only see themselves and user2
        allowed_ids = [self.user1.id, self.user2.id]
        self._setup_rbac_mocks(auth_models.User, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.users_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {user['id'] for user in response.data['results']}
        self.assertEqual(returned_ids, set(allowed_ids))

        # Verify user3, user4, and user5 are not in results
        self.assertNotIn(self.user3.id, returned_ids)
        self.assertNotIn(user4.id, returned_ids)
        self.assertNotIn(user5.id, returned_ids)

    def test_admin_sees_all_users(self):
        """Test that superuser sees all users regardless of RBAC."""
        # Create additional users
        auth_models.User.objects.create(username="user4", is_superuser=False)
        auth_models.User.objects.create(username="user5", is_superuser=False)

        # Admin should see all users
        self._setup_rbac_mocks(auth_models.User, self.admin_user, [])

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.users_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin sees all users (including the test user from BaseTestCase)
        self.assertGreaterEqual(len(response.data['results']), 6)

    def test_group_list_filtered_by_rbac(self):
        """Test that group listing is filtered based on RBAC permissions."""
        group1 = auth_models.Group.objects.create(name="group1")
        group2 = auth_models.Group.objects.create(name="group2")
        group3 = auth_models.Group.objects.create(name="group3")

        # user1 should only see group1 and group2
        allowed_ids = [group1.id, group2.id]
        self._setup_rbac_mocks(auth_models.Group, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.groups_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {group['id'] for group in response.data['results']}
        self.assertEqual(returned_ids, set(allowed_ids))
        self.assertNotIn(group3.id, returned_ids)

    def test_group_retrieve_filtered_by_rbac(self):
        """Test that group retrieval respects RBAC permissions."""
        group1 = auth_models.Group.objects.create(name="group1")
        group2 = auth_models.Group.objects.create(name="group2")

        # user1 should only see group1
        allowed_ids = [group1.id]
        self._setup_rbac_mocks(auth_models.Group, self.user1, allowed_ids)

        with patch(
            'galaxy_ng.app.api.ui.v2.views.AnsibleBaseObjectPermissions.has_object_permission',
            return_value=True
        ):
            self.client.force_authenticate(user=self.user1)

            # Should be able to retrieve allowed group
            response = self.client.get(f"{self.groups_url}{group1.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['id'], group1.id)

            # Should not be able to retrieve disallowed group (filtered by queryset)
            response = self.client.get(f"{self.groups_url}{group2.id}/")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_organization_list_filtered_by_rbac(self):
        """Test that organization listing is filtered based on RBAC permissions."""
        org1 = Organization.objects.create(name="org1")
        org2 = Organization.objects.create(name="org2")
        org3 = Organization.objects.create(name="org3")

        # user1 should only see org1 and org2
        allowed_ids = [org1.id, org2.id]
        self._setup_rbac_mocks(Organization, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.organizations_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {org['id'] for org in response.data['results']}
        self.assertEqual(returned_ids, set(allowed_ids))
        self.assertNotIn(org3.id, returned_ids)

    def test_organization_retrieve_filtered_by_rbac(self):
        """Test that organization retrieval respects RBAC permissions."""
        org1 = Organization.objects.create(name="org1")
        org2 = Organization.objects.create(name="org2")

        # user1 should only see org1
        allowed_ids = [org1.id]
        self._setup_rbac_mocks(Organization, self.user1, allowed_ids)

        with patch(
            'galaxy_ng.app.api.ui.v2.views.AnsibleBaseObjectPermissions.has_object_permission',
            return_value=True
        ):
            self.client.force_authenticate(user=self.user1)

            # Should be able to retrieve allowed organization
            response = self.client.get(f"{self.organizations_url}{org1.id}/")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['id'], org1.id)

            # Should not be able to retrieve disallowed organization (filtered by queryset)
            response = self.client.get(f"{self.organizations_url}{org2.id}/")
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_team_list_filtered_by_rbac(self):
        """Test that team listing is filtered based on RBAC permissions."""
        org = Organization.objects.create(name="test_org")
        team1 = Team.objects.create(name="team1", organization=org)
        team2 = Team.objects.create(name="team2", organization=org)
        team3 = Team.objects.create(name="team3", organization=org)

        # user1 should only see team1 and team2
        allowed_ids = [team1.id, team2.id]
        self._setup_rbac_mocks(Team, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.teams_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {team['id'] for team in response.data['results']}
        self.assertEqual(returned_ids, set(allowed_ids))
        self.assertNotIn(team3.id, returned_ids)

    def test_team_retrieve_filtered_by_rbac(self):
        """Test that team retrieval respects RBAC permissions."""
        org = Organization.objects.create(name="test_org")
        team1 = Team.objects.create(name="team1", organization=org)
        team2 = Team.objects.create(name="team2", organization=org)

        # user1 should only see team1
        allowed_ids = [team1.id]
        self._setup_rbac_mocks(Team, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)

        # Should be able to retrieve allowed team
        response = self.client.get(f"{self.teams_url}{team1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], team1.id)

        # Should not be able to retrieve disallowed team
        response = self.client.get(f"{self.teams_url}{team2.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_rbac_filtering_with_search_parameters(self):
        """Test that RBAC filtering works correctly with search/filter parameters."""
        group1 = auth_models.Group.objects.create(name="test_group1")
        auth_models.Group.objects.create(name="test_group2")
        group3 = auth_models.Group.objects.create(name="another_group")

        # user1 should only see group1 and group3
        allowed_ids = [group1.id, group3.id]
        self._setup_rbac_mocks(auth_models.Group, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)

        # Filter by name
        response = self.client.get(f"{self.groups_url}?name=test_group1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return group1 (allowed and matches filter)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], group1.id)

        # Filter by name that would match group2 but user doesn't have access
        response = self.client.get(f"{self.groups_url}?name=test_group2")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return empty since group2 is not in allowed_ids
        self.assertEqual(len(response.data['results']), 0)

    def test_rbac_filtering_preserves_pagination(self):
        """Test that RBAC filtering works correctly with pagination."""
        # Create multiple users
        for i in range(10):
            auth_models.User.objects.create(username=f"test_user_{i}")

        # user1 should only see first 5 test users
        allowed_ids = [user.id for user in auth_models.User.objects.filter(
            username__startswith="test_user_"
        )[:5]]
        self._setup_rbac_mocks(auth_models.User, self.user1, allowed_ids)

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(f"{self.users_url}?page_size=3")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should respect pagination limit (page_size of 3)
        self.assertLessEqual(len(response.data['results']), 3)
        # All returned users should be in allowed list
        returned_ids = {user['id'] for user in response.data['results']}
        self.assertTrue(returned_ids.issubset(set(allowed_ids)))

    def test_model_not_registered_skips_rbac_filtering(self):
        """Test that models not registered with permission_registry skip RBAC filtering."""
        group1 = auth_models.Group.objects.create(name="group1")
        group2 = auth_models.Group.objects.create(name="group2")

        # Mock permission_registry.is_registered to return False
        with patch(
            'galaxy_ng.app.api.ui.v2.views.permission_registry.is_registered',
            return_value=False
        ):
            self.client.force_authenticate(user=self.user1)
            response = self.client.get(self.groups_url)

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            # Should see all groups since RBAC filtering is skipped
            returned_ids = {group['id'] for group in response.data['results']}
            self.assertIn(group1.id, returned_ids)
            self.assertIn(group2.id, returned_ids)

    def test_empty_queryset_when_no_access(self):
        """Test that users with no access get empty results."""
        auth_models.Group.objects.create(name="group1")
        auth_models.Group.objects.create(name="group2")

        # user1 has no access to any groups
        self._setup_rbac_mocks(auth_models.Group, self.user1, [])

        self.client.force_authenticate(user=self.user1)
        response = self.client.get(self.groups_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
