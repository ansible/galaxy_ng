import logging

from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)


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

    def test_user_list(self):
        def _test_user_list():
            self.client.force_authenticate(user=self.user)
            log.debug("self.client: %s", self.client)
            log.debug("self.client.__dict__: %s", self.client.__dict__)
            response = self.client.get(self.user_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=self.admin_user)
            response = self.client.get(self.user_url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.data["data"]
            self.assertEqual(len(data), auth_models.User.objects.all().count())

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            _test_user_list()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            _test_user_list()

    def test_user_get(self):
        def _test_user_get():
            # Check test user cannot view themselves on the users/ api
            self.client.force_authenticate(user=self.user)
            url = "{}{}/".format(self.user_url, self.user.id)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Check test user cannot view other users
            url = "{}{}/".format(self.user_url, self.admin_user.id)
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            # Check admin user can view others
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
            _test_user_get()

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            _test_user_get()

    def _test_create_or_update(self, method_call, url, new_user_data, crud_status, auth_user):
        self.client.force_authenticate(user=auth_user)
        # set user with invalid password
        new_user_data["password"] = "12345678"
        response = method_call(url, new_user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_messages = set([])
        for err in response.data["errors"]:
            error_messages.add(err["code"])

        desired_errors = set(
            ["password_too_short", "password_too_common", "password_entirely_numeric"]
        )

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

        # user create disabled in insights mode
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self.client.force_authenticate(user=self.admin_user)
            response = self.client.post(self.user_url, new_user_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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

        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            self._test_create_or_update(
                self.client.put, put_url, new_user_data, status.HTTP_200_OK, self.admin_user
            )

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
