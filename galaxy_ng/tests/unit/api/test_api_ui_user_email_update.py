import logging

from django.test import override_settings
from rest_framework import status

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models
from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUserEmailUpdateRestriction(BaseTestCase):
    """Tests that regular users cannot update their own email.

    The enforcement comes from django-ansible-base's pre_save signal
    (rbac_pre_save_enforce_email_policy) which calls can_change_user
    with can_self_edit=False, blocking non-privileged users from
    modifying the email field.
    """

    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(
            username="admin", email="admin@example.com", is_superuser=True,
        )
        self.regular_user = auth_models.User.objects.create(
            username="regular", email="regular@example.com",
        )
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()

        self.me_url = get_current_ui_url("me")
        self.v1_users_url = get_current_ui_url("users-list")
        self.v2_users_url = "/api/galaxy/_ui/v2/users/"

    # ------------------------------------------------------------------ #
    # v1 /me/ endpoint
    # ------------------------------------------------------------------ #

    def test_v1_regular_user_cannot_update_own_email_via_me(self):
        """PUT to /me/ with a new email is rejected for non-superusers."""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "username": self.regular_user.username,
            "first_name": "Regular",
            "last_name": "User",
            "email": "new-email@example.com",
            "groups": [],
        }
        response = self.client.put(self.me_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "You do not have permission to change the email field.",
            str(response.data),
        )
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "regular@example.com")

    def test_v1_regular_user_can_update_profile_without_email_change(self):
        """PUT to /me/ succeeds when the email field is omitted."""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "username": self.regular_user.username,
            "first_name": "Updated",
            "last_name": "Name",
            "groups": [],
        }
        response = self.client.put(self.me_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.first_name, "Updated")
        self.assertEqual(self.regular_user.last_name, "Name")

    def test_v1_regular_user_can_submit_unchanged_email(self):
        """PUT to /me/ with the same email value succeeds."""
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "username": self.regular_user.username,
            "first_name": "Regular",
            "last_name": "User",
            "email": "regular@example.com",
            "groups": [],
        }
        response = self.client.put(self.me_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_v1_email_unchanged_after_rejected_update(self):
        """The email field in the DB remains the original after a rejected change."""
        original_email = self.regular_user.email
        self.client.force_authenticate(user=self.regular_user)
        data = {
            "username": self.regular_user.username,
            "first_name": "Regular",
            "last_name": "User",
            "email": "hacked@example.com",
            "groups": [],
        }
        response = self.client.put(self.me_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, original_email)

    # ------------------------------------------------------------------ #
    # v1 /users/{id}/ endpoint
    # ------------------------------------------------------------------ #

    def test_v1_superuser_can_update_user_email(self):
        """Superuser can change another user's email via /users/{id}/."""
        self.client.force_authenticate(user=self.admin_user)
        url = "{}{}/".format(self.v1_users_url, self.regular_user.id)
        data = {
            "username": self.regular_user.username,
            "first_name": "Regular",
            "last_name": "User",
            "email": "admin-changed@example.com",
            "groups": [],
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "admin-changed@example.com")

    # ------------------------------------------------------------------ #
    # v2 /users/{id}/ endpoint
    # ------------------------------------------------------------------ #

    def test_v2_superuser_can_update_user_email(self):
        """Superuser can change another user's email via v2 API."""
        self.client.force_authenticate(user=self.admin_user)
        url = "{}{}/".format(self.v2_users_url, self.regular_user.id)
        data = {
            "username": self.regular_user.username,
            "first_name": "Regular",
            "last_name": "User",
            "email": "v2-changed@example.com",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "v2-changed@example.com")

    def test_v2_superuser_can_update_own_email(self):
        """Superuser can change their own email via v2 API."""
        self.client.force_authenticate(user=self.admin_user)
        url = "{}{}/".format(self.v2_users_url, self.admin_user.id)
        data = {
            "username": self.admin_user.username,
            "email": "admin-new@example.com",
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.email, "admin-new@example.com")

    def test_v2_regular_user_cannot_update_own_email(self):
        """Regular user is denied when trying to change email via v2 API."""
        self.client.force_authenticate(user=self.regular_user)
        url = "{}{}/".format(self.v2_users_url, self.regular_user.id)
        data = {
            "username": self.regular_user.username,
            "email": "hacked-v2@example.com",
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "regular@example.com")
