import logging
from unittest import mock

from rest_framework import status
from django.urls import reverse
from django.test import override_settings
from pulp_ansible.app.models import AnsibleDistribution, AnsibleRepository, CollectionRemote
from pulpcore.plugin.util import assign_role
from galaxy_ng.app.constants import DeploymentMode
from .base import BaseTestCase

log = logging.getLogger(__name__)


def _create_repo(name, **kwargs):
    repo = AnsibleRepository.objects.create(name=name, **kwargs)
    AnsibleDistribution.objects.create(name=name, base_path=name, repository=repo)
    return repo


def _create_remote(name, url, **kwargs):
    return CollectionRemote.objects.create(name=name, url=url, **kwargs)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestUiSyncConfigViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.admin_user = self._create_user("admin")
        self.sync_group = self._create_group(
            "", "admins", self.admin_user, ["galaxy.collection_admin"]
        )
        self.admin_user.save()

        # Remotes are created by data migration
        self.certified_remote = CollectionRemote.objects.get(name="rh-certified")
        self.community_remote = CollectionRemote.objects.get(name="community")

    def build_config_url(self, path):
        return reverse("galaxy:api:v3:sync-config", kwargs={"path": path})

    def build_sync_url(self, path):
        return reverse("galaxy:api:v3:sync", kwargs={"path": path})

    def test_positive_get_config_sync_for_certified(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.build_config_url(self.certified_remote.name))
        log.debug("test_positive_get_config_sync_for_certified")
        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.data["name"], self.certified_remote.name)
        self.assertEqual(response.data["url"], self.certified_remote.url)
        self.assertEqual(response.data["requirements_file"], None)

    def test_positive_get_config_sync_for_community(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.build_config_url(self.community_remote.name))
        log.debug("test_positive_get_config_sync_for_community")
        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.data["name"], self.community_remote.name)
        self.assertEqual(response.data["url"], self.community_remote.url)
        self.assertEqual(
            response.data["requirements_file"], self.community_remote.requirements_file
        )

    def test_positive_update_certified_repo_data(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            self.build_config_url(self.certified_remote.name),
            {
                "auth_url": "https://auth.com",
                "token": "TEST",
                "name": "rh-certified",
                "policy": "immediate",
                "requirements_file": None,
                "url": "https://updated.url.com/",
            },
            format="json",
        )
        log.debug("test_positive_update_certified_repo_data")
        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        updated = self.client.get(self.build_config_url(self.certified_remote.name))
        self.assertEqual(updated.data["auth_url"], "https://auth.com")
        self.assertEqual(updated.data["url"], "https://updated.url.com/")
        self.assertIsNone(updated.data["requirements_file"])

    def test_negative_update_community_repo_data_without_requirements_file(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "name": "community",
                "policy": "immediate",
                "requirements_file": None,
                "url": "https://beta-galaxy.ansible.com/api/v3/collections",
            },
            format="json",
        )
        log.debug("test_negative_update_community_repo_data_without_requirements_file")
        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "Syncing content from community domains without specifying a "
            "requirements file is not allowed.",
            str(response.data["errors"]),
        )

    def test_positive_update_community_repo_data_with_requirements_file(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "token": "TEST",
                "name": "community",
                "policy": "immediate",
                "requirements_file": (
                    "collections:\n"
                    "  - name: foo.bar\n"
                    "    server: https://foobar.content.com\n"
                    "    api_key: s3cr3tk3y\n"
                ),
                "url": "https://beta-galaxy.ansible.com/api/v3/collections/",
            },
            format="json",
        )

        log.debug("test_positive_update_community_repo_data_with_requirements_file")
        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("foobar.content.com", response.data["requirements_file"])

    def test_negative_put_clears_requirements_file_on_community_remote(self):
        """PUT must not clear requirements_file while url is a community domain."""
        self.client.force_authenticate(user=self.admin_user)
        self.community_remote.url = "https://galaxy.ansible.com/api/"
        self.community_remote.requirements_file = "collections:\n  - name: foo.bar\n"
        self.community_remote.save()

        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "name": "community",
                "policy": "immediate",
                "requirements_file": None,
                "url": "https://galaxy.ansible.com/api/",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "requirements file is not allowed",
            str(response.data),
        )
        self.community_remote.refresh_from_db()
        self.assertIsNotNone(self.community_remote.requirements_file)

    def test_positive_put_community_url_keeps_requirements_file(self):
        """PUT to a community domain is 200 when requirements_file is in the body."""
        self.client.force_authenticate(user=self.admin_user)
        requirements_file = "collections:\n  - name: foo.bar\n"
        self.community_remote.url = "https://example.com/api/"
        self.community_remote.requirements_file = requirements_file
        self.community_remote.save()

        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "token": "TEST",
                "name": "community",
                "policy": "immediate",
                "requirements_file": requirements_file,
                "url": "https://galaxy.ansible.com/api/",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data["url"], "https://galaxy.ansible.com/api/")
        self.assertIn("foo.bar", response.data["requirements_file"])

    def test_negative_put_community_url_without_requirements_file(self):
        """PUT to a community domain is 400 when requirements_file is omitted."""
        self.client.force_authenticate(user=self.admin_user)
        self.community_remote.url = "https://example.com/api/"
        self.community_remote.requirements_file = None
        self.community_remote.save()

        response = self.client.put(
            self.build_config_url(self.community_remote.name),
            {
                "auth_url": "https://auth.com",
                "name": "community",
                "policy": "immediate",
                "requirements_file": None,
                "url": "https://galaxy.ansible.com/api/",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "requirements file is not allowed",
            str(response.data),
        )

    def test_positive_syncing_returns_a_task_id(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(self.build_sync_url(self.certified_remote.name))
        log.debug("test_positive_syncing_returns_a_task_id")
        log.debug("response: %s", response)
        log.debug("response.data: %s", response.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("task", response.data)

    def test_sensitive_fields_are_not_exposed(self):
        self.client.force_authenticate(user=self.admin_user)
        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.get(api_url)
        self.assertNotIn("password", response.data)
        self.assertNotIn("token", response.data)
        self.assertNotIn("proxy_password", response.data)

    def test_write_only_fields(self):
        self.client.force_authenticate(user=self.admin_user)
        api_url = self.build_config_url(self.certified_remote.name)
        write_only_fields = [
            "client_key",
            "token",
            "password",
            "proxy_password",
        ]

        # note, proxy (url, username and password) are required together
        request_data = {
            "url": self.certified_remote.url,
            "proxy_url": "https://example.com",
            "proxy_username": "bob",
            "proxy_password": "1234",
        }

        for field in write_only_fields:
            request_data[field] = "value_is_set"

        self.client.put(api_url, request_data, format="json")

        write_only = self.client.get(api_url).data["write_only_fields"]
        response_names = set()
        # Check that all write only fields are set
        for field in write_only:
            self.assertEqual(field["is_set"], True)

            # unset all write only fields
            request_data[field["name"]] = None
            response_names.add(field["name"])

        # proxy username and password can only be specified together
        request_data["proxy_username"] = None
        self.assertEqual(set(write_only_fields), response_names)
        response = self.client.put(api_url, request_data, format="json")
        self.assertEqual(response.status_code, 200)

        response = self.client.get(api_url)
        self.assertEqual(response.status_code, 200)

        # Check that proxy_username is unset
        self.assertIsNone(response.data["proxy_username"])

        # Check that all write only fields are unset
        write_only = response.data["write_only_fields"]
        for field in write_only:
            self.assertEqual(field["is_set"], False)
            request_data[field["name"]] = ""

        instance = CollectionRemote.objects.get(name=self.certified_remote.name)
        self.assertFalse(instance.proxy_password)

        self.client.put(api_url, request_data, format="json")

        write_only = self.client.get(api_url).data["write_only_fields"]
        for field in write_only:
            self.assertEqual(field["is_set"], False)

    def test_proxy_fields(self):
        self.client.force_authenticate(user=self.admin_user)

        # ensure proxy_url is blank
        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.get(api_url)
        self.assertIsNone(response.data["proxy_url"])

        data = {"name": response.data["name"], "url": response.data["url"]}

        # PUT proxy url without auth
        self.client.put(api_url, {"proxy_url": "http://proxy.com:4242", **data}, format="json")
        response = self.client.get(api_url)
        self.assertEqual(response.data["proxy_url"], "http://proxy.com:4242")
        self.assertNotIn("proxy_password", response.data)
        self.assertIn("proxy_username", response.data)
        instance = CollectionRemote.objects.get(pk=response.data["pk"])
        self.assertEqual(instance.proxy_url, "http://proxy.com:4242")

        # PUT proxy url with username and password
        self.client.put(
            api_url,
            {
                "proxy_url": "http://proxy.com:4242",
                "proxy_username": "User1",
                "proxy_password": "MyPrecious42",
                **data,
            },
            format="json",
        )
        response = self.client.get(api_url)
        self.assertEqual(response.data["proxy_url"], "http://proxy.com:4242")
        self.assertNotIn("proxy_password", response.data)
        self.assertIn("proxy_username", response.data)
        instance = CollectionRemote.objects.get(pk=response.data["pk"])
        self.assertEqual(instance.proxy_url, "http://proxy.com:4242")
        self.assertEqual(instance.proxy_username, "User1")
        self.assertEqual(instance.proxy_password, "MyPrecious42")

        # Edit url using IP
        self.client.put(api_url, {"proxy_url": "http://192.168.0.42:4242", **data}, format="json")
        response = self.client.get(api_url)
        self.assertEqual(response.data["proxy_url"], "http://192.168.0.42:4242")
        self.assertNotIn("proxy_password", response.data)
        self.assertIn("proxy_username", response.data)
        instance = CollectionRemote.objects.get(pk=response.data["pk"])
        self.assertEqual(instance.proxy_url, "http://192.168.0.42:4242")
        self.assertEqual(instance.proxy_password, "MyPrecious42")

        # Edit url
        self.client.put(api_url, {"proxy_url": "http://proxy2.com:4242", **data}, format="json")
        response = self.client.get(api_url)
        self.assertEqual(response.data["proxy_url"], "http://proxy2.com:4242")
        self.assertNotIn("proxy_password", response.data)
        self.assertIn("proxy_username", response.data)
        instance = CollectionRemote.objects.get(pk=response.data["pk"])
        self.assertEqual(instance.proxy_url, "http://proxy2.com:4242")
        self.assertEqual(instance.proxy_password, "MyPrecious42")

    def _proxy_sync_put_body(self, remote, **extra):
        body = {
            "name": remote.name,
            "url": remote.url,
            "proxy_url": remote.proxy_url,
            "proxy_username": remote.proxy_username,
            "proxy_password": None,
        }
        body.update(extra)
        return body

    def test_put_explicit_null_clears_proxy_password(self):
        self.client.force_authenticate(user=self.admin_user)
        self.certified_remote.proxy_url = "http://proxy.example.com:4242"
        self.certified_remote.proxy_username = "certified-user"
        self.certified_remote.proxy_password = "clear-me"
        self.certified_remote.save()

        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.put(
            api_url,
            self._proxy_sync_put_body(
                self.certified_remote,
                proxy_username=None,
                proxy_password=None,
            ),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.certified_remote.refresh_from_db()
        self.assertFalse(self.certified_remote.proxy_password)
        self.assertIsNone(self.certified_remote.proxy_username)

    def test_put_write_only_fields_hints_do_not_500(self):
        self.client.force_authenticate(user=self.admin_user)
        self.certified_remote.proxy_url = "http://proxy.example.com:4242"
        self.certified_remote.proxy_username = "certified-user"
        self.certified_remote.proxy_password = "still-here"
        self.certified_remote.save()
        api_url = self.build_config_url(self.certified_remote.name)

        keep_proxy_hint = {"name": "proxy_password", "is_set": True}
        # Well-formed lists: keep-hint restores; absent/empty do not (Pulp pairing 400).
        valid_cases = {
            "absent": ({}, status.HTTP_400_BAD_REQUEST),
            "empty_list": ({"write_only_fields": []}, status.HTTP_400_BAD_REQUEST),
            "non_proxy_only": (
                {"write_only_fields": [{"name": "token", "is_set": True}]},
                status.HTTP_400_BAD_REQUEST,
            ),
            "non_proxy_plus_keep": (
                {
                    "write_only_fields": [
                        {"name": "token", "is_set": True},
                        keep_proxy_hint,
                    ]
                },
                status.HTTP_200_OK,
            ),
        }
        for label, (hint_extra, expected_status) in valid_cases.items():
            with self.subTest(hint=label):
                body = {
                    "name": self.certified_remote.name,
                    "url": "https://updated-for-hints.example.com/",
                    "proxy_url": self.certified_remote.proxy_url,
                    "proxy_username": self.certified_remote.proxy_username,
                    "proxy_password": None,
                    **hint_extra,
                }
                response = self.client.put(api_url, body, format="json")
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response.data,
                )
                self.assertEqual(response.status_code, expected_status, response.data)

        # Malformed shapes must be 400 from serializer validation, never 500.
        invalid_cases = {
            "non_dict_entry": {"write_only_fields": ["token", keep_proxy_hint]},
            "dict_without_name": {
                "write_only_fields": [
                    {"is_set": True},
                    keep_proxy_hint,
                ]
            },
            "non_list": {"write_only_fields": keep_proxy_hint},
        }
        for label, hint_extra in invalid_cases.items():
            with self.subTest(hint=label):
                body = {
                    "name": self.certified_remote.name,
                    "url": "https://updated-for-hints.example.com/",
                    "proxy_url": self.certified_remote.proxy_url,
                    "proxy_username": self.certified_remote.proxy_username,
                    "proxy_password": None,
                    **hint_extra,
                }
                response = self.client.put(api_url, body, format="json")
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response.data,
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                    response.data,
                )

        self.certified_remote.refresh_from_db()
        self.assertEqual(self.certified_remote.proxy_password, "still-here")

    def test_write_only_hint_preserves_this_remote_proxy_password_on_put(self):
        self.client.force_authenticate(user=self.admin_user)
        self.certified_remote.proxy_url = "http://proxy.example.com:4242"
        self.certified_remote.proxy_username = "certified-user"
        self.certified_remote.proxy_password = "certified-secret"
        self.certified_remote.save()

        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.put(
            api_url,
            {
                "name": self.certified_remote.name,
                "url": self.certified_remote.url,
                "proxy_url": "http://proxy.example.com:4242",
                "proxy_username": "certified-user",
                "proxy_password": None,
                "write_only_fields": [{"name": "proxy_password", "is_set": True}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.certified_remote.refresh_from_db()
        self.assertEqual(self.certified_remote.proxy_password, "certified-secret")

    def test_put_new_password_with_keep_hint_replaces_proxy_password(self):
        self.client.force_authenticate(user=self.admin_user)
        self.certified_remote.proxy_url = "http://proxy.example.com:4242"
        self.certified_remote.proxy_username = "certified-user"
        self.certified_remote.proxy_password = "old-secret"
        self.certified_remote.save()

        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.put(
            api_url,
            {
                "name": self.certified_remote.name,
                "url": self.certified_remote.url,
                "proxy_url": "http://proxy.example.com:4242",
                "proxy_username": "certified-user",
                "proxy_password": "brand-new-secret",
                "write_only_fields": [{"name": "proxy_password", "is_set": True}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.certified_remote.refresh_from_db()
        self.assertEqual(self.certified_remote.proxy_password, "brand-new-secret")

    def test_write_only_hint_does_not_copy_another_remote_proxy_password_on_put(self):
        self.client.force_authenticate(user=self.admin_user)
        other = CollectionRemote.objects.create(
            name="other-sync-proxy-remote",
            url="https://other.example.com/api/",
            proxy_url="http://proxy.example.com:4242",
            proxy_username="other-user",
            proxy_password="other-secret",
        )
        self.certified_remote.proxy_url = "http://proxy.example.com:4242"
        self.certified_remote.proxy_username = "certified-user"
        self.certified_remote.proxy_password = "certified-secret"
        self.certified_remote.save()

        api_url = self.build_config_url(self.certified_remote.name)
        response = self.client.put(
            api_url,
            {
                "name": other.name,
                "url": self.certified_remote.url,
                "proxy_url": "http://proxy.example.com:4242",
                "proxy_username": "certified-user",
                "proxy_password": None,
                "write_only_fields": [{"name": "proxy_password", "is_set": True}],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.certified_remote.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(self.certified_remote.proxy_password, "certified-secret")
        self.assertEqual(other.proxy_password, "other-secret")

    def _stale_remote_href(self):
        stale = CollectionRemote.objects.create(
            name="stale-sync-body-remote",
            url="https://example.invalid/api/",
        )
        href = f"/pulp/api/v3/remotes/ansible/collection/{stale.pk}/"
        stale.delete()
        return href

    def _post_sync(self, path, body=None):
        url = self.build_sync_url(path)
        if body is None:
            return self.client.post(url)
        return self.client.post(url, body, format="json")

    def test_sync_body_remote_does_not_500(self):
        """Empty, malformed, and stale request-body remotes must not 500.

        This endpoint ignores request.data['remote'] and always syncs the
        distribution's linked remote. A leftover policy condition used to
        resolve that field and crash on a stale or malformed value.
        """
        self.client.force_authenticate(user=self.admin_user)
        bodies = {
            "empty": None,
            "malformed": {"remote": "not-a-remote"},
            "stale": {"remote": self._stale_remote_href()},
        }

        with mock.patch("galaxy_ng.app.api.v3.views.sync.dispatch") as mock_dispatch:
            mock_dispatch.return_value = mock.Mock(pk="task-id")
            for label, body in bodies.items():
                with self.subTest(body=label):
                    response = self._post_sync(self.certified_remote.name, body)
                    self.assertNotEqual(
                        response.status_code,
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        response.data,
                    )
                    self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                    self.assertIn("task", response.data)

    def test_sync_linked_remote_without_requirements_returns_400(self):
        """A community linked remote without requirements_file is 400.

        Dispatch must not run. A stale or malformed body remote must not
        change this into a 500.
        """
        self.client.force_authenticate(user=self.admin_user)
        self.community_remote.url = "https://galaxy.ansible.com/api/"
        self.community_remote.requirements_file = None
        self.community_remote.save()

        bodies = {
            "empty": None,
            "malformed": {"remote": "not-a-remote"},
            "stale": {"remote": self._stale_remote_href()},
        }

        with mock.patch("galaxy_ng.app.api.v3.views.sync.dispatch") as mock_dispatch:
            for label, body in bodies.items():
                with self.subTest(body=label):
                    response = self._post_sync(self.community_remote.name, body)
                    self.assertEqual(
                        response.status_code, status.HTTP_400_BAD_REQUEST, response.data
                    )
                    self.assertIn(
                        "requirements file is not allowed",
                        str(response.data),
                    )
            mock_dispatch.assert_not_called()

    def test_sync_uses_distribution_linked_remote_not_body_remote(self):
        """A valid sync must dispatch the distribution's linked remote."""
        self.client.force_authenticate(user=self.admin_user)
        body_remote = CollectionRemote.objects.create(
            name="body-supplied-sync-remote",
            url="https://galaxy.ansible.com/api/",
            requirements_file=None,
        )
        body_href = f"/pulp/api/v3/remotes/ansible/collection/{body_remote.pk}/"

        with mock.patch("galaxy_ng.app.api.v3.views.sync.dispatch") as mock_dispatch:
            mock_dispatch.return_value = mock.Mock(pk="task-id")
            response = self._post_sync(self.certified_remote.name, {"remote": body_href})

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        mock_dispatch.assert_called_once()
        dispatched_remote_pk = mock_dispatch.call_args.kwargs["kwargs"]["remote_pk"]
        self.assertEqual(dispatched_remote_pk, self.certified_remote.pk)
        self.assertNotEqual(dispatched_remote_pk, body_remote.pk)

    def _certified_put_payload(self, **overrides):
        payload = {
            "auth_url": "https://auth.com",
            "token": "TEST",
            "name": "rh-certified",
            "policy": "immediate",
            "requirements_file": None,
            "url": "https://updated.url.com/",
        }
        payload.update(overrides)
        return payload

    def _assert_config_methods_status(self, path, expected_status, user, put_payload=None):
        """GET and PUT on sync/config must both return expected_status (never 500)."""
        self.client.force_authenticate(user=user)
        url = self.build_config_url(path)
        payload = put_payload if put_payload is not None else self._certified_put_payload()

        for method in ("get", "put"):
            with self.subTest(method=method, path=path):
                if method == "get":
                    response = self.client.get(url)
                else:
                    response = self.client.put(url, payload, format="json")
                self.assertNotEqual(
                    response.status_code,
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    response.data,
                )
                self.assertEqual(response.status_code, expected_status, response.data)

    def test_unprivileged_missing_path_returns_404(self):
        """Unprivileged GET/PUT on a nonexistent base path must be 404, never 500."""
        self._assert_config_methods_status("does-not-exist", status.HTTP_404_NOT_FOUND, self.user)

    def test_unprivileged_published_no_remote_returns_404(self):
        """Unprivileged GET/PUT on published (no remote) must be 404, never 500."""
        published = AnsibleDistribution.objects.get(base_path="published")
        self.assertIsNotNone(published.repository)
        self.assertIsNone(published.repository.remote)

        self._assert_config_methods_status("published", status.HTTP_404_NOT_FOUND, self.user)

    def test_unprivileged_put_rh_certified_returns_403(self):
        """Unprivileged PUT on rh-certified must be 403 (object exists; no change perm)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.put(
            self.build_config_url(self.certified_remote.name),
            self._certified_put_payload(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.data)

    def test_object_level_owner_put_rh_certified_returns_200(self):
        """Object-level change_collectionremote on rh-certified remote allows PUT 200."""
        owner = self._create_user("rh_certified_remote_owner")
        assign_role(
            "galaxy.collection_remote_owner",
            owner,
            obj=self.certified_remote,
        )
        self.client.force_authenticate(user=owner)
        response = self.client.put(
            self.build_config_url(self.certified_remote.name),
            self._certified_put_payload(url="https://owner-updated.url.com/"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.certified_remote.refresh_from_db()
        self.assertEqual(self.certified_remote.url, "https://owner-updated.url.com/")

    def test_admin_missing_and_no_remote_paths_return_404(self):
        """Admin GET/PUT on missing or no-remote paths must be 404, never 500."""
        self._assert_config_methods_status(
            "does-not-exist", status.HTTP_404_NOT_FOUND, self.admin_user
        )
        self._assert_config_methods_status("published", status.HTTP_404_NOT_FOUND, self.admin_user)


@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
class TestSyncPermissionRoleMatrix(BaseTestCase):
    """Real role-assignment matrix for POST /content/<path>/v3/sync/.

    Sync requires change_collectionremote plus repository permission
    (modify_ansible_repo_content or change_ansiblerepository). Config GET/PUT
    still use remote permission only.
    """

    UNREACHABLE_URL = "https://127.0.0.1:1/api/"

    def setUp(self):
        super().setUp()
        self.remote = CollectionRemote.objects.create(
            name="sync-perm-matrix-remote",
            url=self.UNREACHABLE_URL,
        )
        self.repo = AnsibleRepository.objects.create(
            name="sync-perm-matrix-repo",
            remote=self.remote,
        )
        self.distro = AnsibleDistribution.objects.create(
            name="sync-perm-matrix-distro",
            base_path="sync-perm-matrix-distro",
            repository=self.repo,
        )
        self.sync_url = reverse("galaxy:api:v3:sync", kwargs={"path": self.distro.base_path})
        self.config_url = reverse(
            "galaxy:api:v3:sync-config", kwargs={"path": self.distro.base_path}
        )

    def _config_put_payload(self, **overrides):
        payload = {
            "name": self.remote.name,
            "url": self.UNREACHABLE_URL,
            "policy": "immediate",
            "requirements_file": None,
            "auth_url": None,
            "token": None,
        }
        payload.update(overrides)
        return payload

    def _assert_config_unchanged_behavior(self, user, put_expected_status):
        """GET/PUT sync/config must match pre-change remote-permission behavior."""
        self.client.force_authenticate(user=user)
        get_response = self.client.get(self.config_url)
        self.assertEqual(get_response.status_code, status.HTTP_200_OK, get_response.data)

        put_response = self.client.put(
            self.config_url,
            self._config_put_payload(url="https://127.0.0.1:1/updated/"),
            format="json",
        )
        self.assertEqual(put_response.status_code, put_expected_status, put_response.data)

    def _assert_sync_status(self, user, expected_status):
        self.client.force_authenticate(user=user)
        with mock.patch("galaxy_ng.app.api.v3.views.sync.dispatch") as mock_dispatch:
            mock_dispatch.return_value = mock.Mock(pk="task-id")
            response = self.client.post(self.sync_url)
            self.assertEqual(response.status_code, expected_status, response.data)
            if expected_status == status.HTTP_200_OK:
                mock_dispatch.assert_called_once()
                self.assertIn("task", response.data)
            else:
                mock_dispatch.assert_not_called()

    def test_global_collection_remote_owner_only_denied_sync(self):
        user = self._create_user("global_remote_owner_only")
        # Assign via group: pulp UserRole for this locked role carries a
        # content type, so DAB rejects assign_role(..., user) without an object.
        self._create_group("", "global_remote_owners", user, ["galaxy.collection_remote_owner"])

        self._assert_sync_status(user, status.HTTP_403_FORBIDDEN)
        self._assert_config_unchanged_behavior(user, status.HTTP_200_OK)

    def test_global_collection_curator_allowed_sync(self):
        user = self._create_user("global_collection_curator")
        self._create_group("", "global_curators", user, ["galaxy.collection_curator"])

        self._assert_sync_status(user, status.HTTP_200_OK)
        self._assert_config_unchanged_behavior(user, status.HTTP_200_OK)

    def test_object_remote_and_repo_owner_allowed_sync(self):
        user = self._create_user("object_remote_and_repo_owner")
        assign_role("galaxy.collection_remote_owner", user, obj=self.remote)
        assign_role("galaxy.ansible_repository_owner", user, obj=self.repo)

        self._assert_sync_status(user, status.HTTP_200_OK)
        self._assert_config_unchanged_behavior(user, status.HTTP_200_OK)

    def test_object_remote_owner_only_denied_sync(self):
        user = self._create_user("object_remote_owner_only")
        assign_role("galaxy.collection_remote_owner", user, obj=self.remote)

        self._assert_sync_status(user, status.HTTP_403_FORBIDDEN)
        self._assert_config_unchanged_behavior(user, status.HTTP_200_OK)
