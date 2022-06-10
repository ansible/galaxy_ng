import logging
import unittest

from django.test import override_settings
from django.conf import settings
from rest_framework import status as http_code

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.constants import DeploymentMode

from . import base
from . import rh_auth
from .synclist_base import BaseSyncListViewSet, ACCOUNT_SCOPE

log = logging.getLogger(__name__)


class BaseUiSynclistViewSet:
    """Test SyncListViewSet as an admin / pe_group member"""

    def setUp(self):
        super().setUp()
        if settings.GALAXY_DEPLOYMENT_MODE != DeploymentMode.INSIGHTS.value:
            raise unittest.SkipTest("Skipping insights mode tests since we are in standalone mode.")

        self.account_number = "987654"
        self.user = auth_models.User.objects.create(username="admin")
        self.group = self._create_partner_engineer_group()
        self.user.groups.add(self.group)
        self.user.save()

        self.synclist_name = "test_synclist"
        self.synclist = self._create_synclist(
            name=self.synclist_name,
            repository=self.repo,
            upstream_repository=self.default_repo,
            groups=[self.group],
        )

        self.synclist.save()

        self.client.force_authenticate(user=None)

    def _group(self, user_group, perms=None):
        perms = perms or self.default_owner_permissions
        group = {
            "id": user_group.id,
            "name": user_group.name,
            "object_permissions": perms,
        }
        return group

    def test_synclist_create(self):
        new_synclist_name = "new_synclist"
        post_data = {
            "repository": self.repo.pk,
            "collections": [],
            "namespaces": [],
            "policy": "include",
            "name": new_synclist_name,
            "groups": [self._group(self.group)],
        }

        synclists_url = base.get_current_ui_url("synclists-list")

        log.debug("self.synclist: %s", self.synclist)

        response = self.client.post(synclists_url, post_data, format="json")

        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)

        self.assertEqual(response.status_code, http_code.HTTP_201_CREATED, msg=response.data)

    def test_synclist_update(self):
        ns1_name = "unittestnamespace1"
        ns2_name = "unittestnamespace2"
        ns1 = self._create_namespace(ns1_name, groups=[self.group])
        ns2 = self._create_namespace(ns2_name, groups=[self.group])
        ns1.save()
        ns2.save()

        post_data = {
            "repository": self.repo.pk,
            "collections": [],
            "namespaces": [ns1_name, ns2_name],
            "policy": "include",
            "groups": [self._group(self.group)],
        }

        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.patch(synclists_detail_url, post_data, format="json")

        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)

        self.assertEqual(response.status_code, http_code.HTTP_200_OK, msg=response.data)
        self.assertIn("name", response.data)
        self.assertIn("repository", response.data)
        self.assertEqual(response.data["name"], self.synclist_name)
        self.assertEqual(response.data["policy"], "include")

    def test_synclist_list(self):
        log.debug('GALAXY_DEPLOYMENT_MODE: %s', settings.GALAXY_DEPLOYMENT_MODE)

        synclists_url = base.get_current_ui_url("synclists-list")
        response = self.client.get(synclists_url)

        log.debug("response.data: %s", response.data)

        self.assertEqual(response.status_code, http_code.HTTP_200_OK, msg=response.data)

    def test_synclist_list_empty(self):
        synclists_url = base.get_current_ui_url("synclists-list")

        response = self.client.get(synclists_url)

        log.debug("response: %s", response)
        log.debug("data: %s", response.data)

        self.assertEqual(response.status_code, http_code.HTTP_200_OK, msg=response.data)

    def test_synclist_detail(self):
        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.get(synclists_detail_url)

        self.assertEqual(response.status_code, http_code.HTTP_200_OK, msg=response.data)
        self.assertIn("name", response.data)
        self.assertIn("repository", response.data)
        self.assertEqual(response.data["name"], self.synclist_name)
        self.assertEqual(response.data["policy"], "exclude")
        self.assertEqual(response.data["collections"], [])
        self.assertEqual(response.data["namespaces"], [])

    def test_synclist_delete(self):
        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        log.debug("delete url: %s", synclists_detail_url)

        response = self.client.delete(synclists_detail_url)

        log.debug("delete response: %s", response)

        self.assertEqual(response.status_code, http_code.HTTP_204_NO_CONTENT, msg=response.data)


@override_settings(
    GALAXY_AUTHENTICATION_CLASSES=["galaxy_ng.app.auth.auth.RHIdentityAuthentication"],
)
class TestUiSynclistViewSetWithGroupPerms(BaseUiSynclistViewSet, BaseSyncListViewSet):
    def setUp(self):
        super().setUp()
        if settings.GALAXY_DEPLOYMENT_MODE != DeploymentMode.INSIGHTS.value:
            raise unittest.SkipTest("Skipping insights mode tests since we are in standalone mode.")

        self.user = auth_models.User.objects.create_user(username="test1", password="test1-secret")
        self.group = self._create_group_with_synclist_perms(
            ACCOUNT_SCOPE, self.account_number, users=[self.user]
        )
        self.user.save()
        self.group.save()

        self.user.groups.add(self.group)
        self.user.save()

        self.synclist_name = "test_synclist"
        self.synclist = self._create_synclist(
            name=self.synclist_name,
            repository=self.repo,
            upstream_repository=self.default_repo,
            groups=[self.group],
        )

        self.credentials()

    def credentials(self):
        x_rh_identity = rh_auth.user_x_rh_identity(self.user.username, self.group.account_number())
        log.debug('x_rh_identity: %s', x_rh_identity)

        self.client.credentials(HTTP_X_RH_IDENTITY=x_rh_identity)
        log.debug('self.client.credentials: %s', self.client.credentials)


class DeniedSynclistViewSet(BaseUiSynclistViewSet):
    def setUp(self):
        super().setUp()

    def test_synclist_create(self):
        post_data = {
            "repository": self.repo.pk,
            "collections": [],
            "namespaces": [],
            "policy": "include",
            "name": "new_synclist",
            "groups": [self._group(self.group)],
        }

        synclists_url = base.get_current_ui_url("synclists-list")
        response = self.client.post(synclists_url, post_data, format="json")

        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)

    def test_synclist_detail(self):
        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.get(synclists_detail_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)

    def test_synclist_list(self):
        synclists_url = base.get_current_ui_url("synclists-list")
        response = self.client.get(synclists_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)

    def test_synclist_list_empty(self):
        synclists_url = base.get_current_ui_url("synclists-list")
        response = self.client.get(synclists_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)

    def test_synclist_update(self):
        post_data = {
            "repository": self.repo.pk,
            "collections": [],
            "namespaces": [],
            "policy": "include",
            "groups": [self._group(self.group)],
        }

        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.patch(synclists_detail_url, post_data, format="json")

        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)

    def test_synclist_delete(self):
        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.delete(synclists_detail_url)
        self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)


@override_settings(
    GALAXY_AUTHENTICATION_CLASSES=["galaxy_ng.app.auth.auth.RHIdentityAuthentication"],
)
class TestUiSynclistViewSetWithDefaultGroupPerms(DeniedSynclistViewSet, BaseSyncListViewSet):
    def setUp(self):
        super().setUp()
        if settings.GALAXY_DEPLOYMENT_MODE != DeploymentMode.INSIGHTS.value:
            raise unittest.SkipTest("Skipping insights mode tests since we are in standalone mode.")

        self.user = auth_models.User.objects.create_user(username="test1", password="test1-secret")
        self.group = self._create_group(ACCOUNT_SCOPE, self.account_number, users=[self.user])
        self.user.save()
        self.group.save()

        self.user.groups.add(self.group)
        self.user.save()

        self.synclist_name = "test_synclist"
        self.synclist = self._create_synclist(
            name=self.synclist_name,
            repository=self.repo,
            upstream_repository=self.default_repo,
            groups=[self.group],
        )

        self.credentials()

    def credentials(self):
        x_rh_identity = rh_auth.user_x_rh_identity(self.user.username, self.group.account_number())
        self.client.credentials(HTTP_X_RH_IDENTITY=x_rh_identity)

    def test_synclist_detail(self):
        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.get(synclists_detail_url)

        # If we created the synclist with group perms directly, we can GET detail
        self.assertEqual(response.status_code, http_code.HTTP_200_OK, msg=response.data)
        self.assertIn("name", response.data)
        self.assertIn("repository", response.data)
        self.assertEqual(response.data["name"], self.synclist_name)
        self.assertEqual(response.data["policy"], "exclude")
        self.assertEqual(response.data["collections"], [])
        self.assertEqual(response.data["namespaces"], [])

    def test_synclist_update(self):
        ns1_name = "unittestnamespace1"
        ns1 = self._create_namespace(ns1_name, groups=[self.group])
        ns1.save()

        post_data = {
            "repository": self.repo.pk,
            "collections": [],
            "namespaces": [ns1_name],
            "policy": "include",
            "groups": [self._group(self.group)],
        }

        synclists_detail_url = base.get_current_ui_url(
            "synclists-detail", kwargs={"pk": self.synclist.id}
        )

        response = self.client.patch(synclists_detail_url, post_data, format="json")

        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)

        # If we created the synclist with group perms directly, we can modify it
        self.assertEqual(response.status_code, http_code.HTTP_200_OK, msg=response.data)
        self.assertIn("name", response.data)
        self.assertIn("repository", response.data)
        self.assertEqual(response.data["name"], self.synclist_name)
        self.assertEqual(response.data["policy"], "include")


@override_settings(
    GALAXY_AUTHENTICATION_CLASSES=["galaxy_ng.app.auth.auth.RHIdentityAuthentication"],
)
class TestUiSynclistViewSetNoGroupPerms(DeniedSynclistViewSet, BaseSyncListViewSet):
    def setUp(self):
        super().setUp()
        if settings.GALAXY_DEPLOYMENT_MODE != DeploymentMode.INSIGHTS.value:
            raise unittest.SkipTest("Skipping insights mode tests since we are in standalone mode.")
        self.user = auth_models.User.objects.create_user(
            username="test_user_noperms", password="test1-secret"
        )
        self.group = self._create_group(ACCOUNT_SCOPE, self.account_number, users=[self.user])
        self.user.save()
        self.group.save()

        self.group.save()

        self.synclist_name = "test_synclist"
        self.synclist = self._create_synclist(
            name=self.synclist_name,
            repository=self.repo,
            upstream_repository=self.default_repo,
            groups=[self.group],
        )

        self.credentials()
        self.client.force_authenticate(user=self.user)

    def credentials(self):
        x_rh_identity = rh_auth.user_x_rh_identity(self.user.username, self.group.account_number())
        self.client.credentials(HTTP_X_RH_IDENTITY=x_rh_identity)
