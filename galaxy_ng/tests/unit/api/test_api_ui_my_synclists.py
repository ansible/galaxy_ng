import logging

from django.conf import settings
from django.apps import apps

from rest_framework import status as http_code

from galaxy_ng.app.models import auth as auth_models
from galaxy_ng.app.constants import DeploymentMode
from . import base

from .synclist_base import BaseSyncListViewSet, ACCOUNT_SCOPE

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)

log.info("settings.FIXTURE_DIRS(module scope): %s", settings.FIXTURE_DIRS)


class TestUiMySyncListViewSet(BaseSyncListViewSet):
    def setUp(self):
        super().setUp()

        log.info("self.fixtures2: %s", self.fixtures)
        log.info("settings.FIXTURE_DIRS2: %s", settings.FIXTURE_DIRS)

        self.user = auth_models.User.objects.create_user(username="test1", password="test1-secret")
        self.group = self._create_group_with_synclist_perms(
            ACCOUNT_SCOPE, "test1_group", users=[self.user]
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

        self.client.force_authenticate(user=self.user)

    def test_my_synclist_create(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            galaxy_app_config = apps.get_app_config("galaxy")
            log.info("gac module: %s", galaxy_app_config.module)
            log.info("gac path: %s", galaxy_app_config.path)

            post_data = {
                "repository": self.repo.pk,
                "collections": [],
                "namespaces": [],
                "policy": "include",
                "groups": [
                    {
                        "id": self.group.id,
                        "name": self.group.name,
                        "object_roles": self.default_owner_roles,
                    },
                ],
            }

            synclists_url = base.get_current_ui_url("my-synclists-list")

            response = self.client.post(synclists_url, post_data, format="json")

            log.debug("response: %s", response)
            log.debug("response.data: %s", response.data)

            # synclist create is not allowed via my-synclist viewset
            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN, msg=response.data)

    def test_my_synclist_update(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            ns_name = "unittestnamespace1"
            ns = self._create_namespace(ns_name, groups=[self.group])
            ns.save()

            post_data = {
                "repository": self.repo.pk,
                "collections": [],
                "namespaces": [ns_name],
                "policy": "include",
                "groups": [
                    {
                        "id": self.group.id,
                        "name": self.group.name,
                        "object_roles": self.default_owner_roles,
                    },
                ],
            }

            synclists_detail_url = base.get_current_ui_url(
                "my-synclists-detail", kwargs={"pk": self.synclist.id}
            )

            response = self.client.patch(synclists_detail_url, post_data, format="json")

            log.debug("response: %s", response)
            log.debug("response.data: %s", response.data)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            self.assertIn("name", response.data)
            self.assertIn("repository", response.data)
            self.assertEqual(response.data["name"], self.synclist_name)
            self.assertEqual(response.data["policy"], "include")

            # Sort role list for comparison
            response.data["groups"][0]["object_roles"].sort()
            self.default_owner_roles.sort()
            self.assertEqual(
                response.data["groups"],
                [
                    {
                        "name": self.group.name,
                        "id": self.group.id,
                        "object_roles": self.default_owner_roles
                    }
                ],
            )

    def test_my_synclist_list(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            synclists_url = base.get_current_ui_url("my-synclists-list")
            log.debug("synclists_url: %s", synclists_url)

            response = self.client.get(synclists_url)

            log.debug("response: %s", response)
            data = response.data["data"]

            self.assertIsInstance(data, list)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]["name"], self.synclist_name)
            self.assertEqual(data[0]["policy"], "exclude")
            self.assertEqual(data[0]["repository"], self.repo.pk)

    def test_my_synclist_detail(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            synclists_detail_url = base.get_current_ui_url(
                "my-synclists-detail", kwargs={"pk": self.synclist.id}
            )

            log.debug("synclists_detail_url: %s", synclists_detail_url)

            response = self.client.get(synclists_detail_url)

            log.debug("response: %s", response)

            self.assertEqual(response.status_code, http_code.HTTP_200_OK)
            self.assertIn("name", response.data)
            self.assertIn("repository", response.data)
            self.assertEqual(response.data["name"], self.synclist_name)
            self.assertEqual(response.data["policy"], "exclude")
            self.assertEqual(response.data["collections"], [])
            self.assertEqual(response.data["namespaces"], [])

    def test_my_synclist_delete(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.INSIGHTS.value):
            synclists_detail_url = base.get_current_ui_url(
                "my-synclists-detail", kwargs={"pk": self.synclist.id}
            )

            log.debug("delete url: %s", synclists_detail_url)

            response = self.client.delete(synclists_detail_url)

            log.debug("delete response: %s", response)

            self.assertEqual(response.status_code, http_code.HTTP_403_FORBIDDEN)
