from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings
from pulpcore.app.models.status import AppStatus
from pulpcore.app.views.status import StatusView as PulpStatusView
from rest_framework.test import APIRequestFactory

from galaxy_ng.app.views import StatusViewSet


@override_settings(CACHE_ENABLED=True)
class TestStatusViewSet(SimpleTestCase):
    def request_status(self):
        request = APIRequestFactory().get("/api/galaxy/status/")
        request.META["REMOTE_ADDR"] = "10.0.0.1"
        return StatusViewSet.as_view({"get": "list"})(request)

    @staticmethod
    def online_apps(api_apps_available, workers_available, content_apps_available):
        online_apps = Mock()
        api_apps = Mock()
        worker_apps = Mock()
        content_apps = Mock()
        api_apps.exists.return_value = api_apps_available
        worker_apps.exists.return_value = workers_available
        content_apps.exists.return_value = content_apps_available
        online_apps.filter.side_effect = [api_apps, worker_apps, content_apps]
        return online_apps

    def test_good_status(self):
        online_apps = self.online_apps(True, True, True)
        with (
            patch.object(PulpStatusView, "_get_db_conn_status", return_value=True),
            patch.object(PulpStatusView, "_get_redis_conn_status", return_value=True),
            patch.object(AppStatus.objects, "online", return_value=online_apps),
        ):
            response = self.request_status()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "good", "issues": []})

    def test_redis_unavailable_is_degraded(self):
        online_apps = self.online_apps(True, True, True)
        with (
            patch.object(PulpStatusView, "_get_db_conn_status", return_value=True),
            patch.object(PulpStatusView, "_get_redis_conn_status", return_value=False),
            patch.object(AppStatus.objects, "online", return_value=online_apps),
        ):
            response = self.request_status()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "status": "degraded",
            "issues": ["redis_unavailable"],
        })

    def test_disabled_redis_is_not_an_issue(self):
        online_apps = self.online_apps(True, True, True)
        with (
            override_settings(CACHE_ENABLED=False),
            patch.object(PulpStatusView, "_get_db_conn_status", return_value=True),
            patch.object(PulpStatusView, "_get_redis_conn_status") as redis_status,
            patch.object(AppStatus.objects, "online", return_value=online_apps),
        ):
            response = self.request_status()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "good", "issues": []})
        redis_status.assert_not_called()

    def test_degraded_status_lists_unavailable_apps(self):
        online_apps = self.online_apps(False, False, False)
        with (
            patch.object(PulpStatusView, "_get_db_conn_status", return_value=True),
            patch.object(PulpStatusView, "_get_redis_conn_status", return_value=True),
            patch.object(AppStatus.objects, "online", return_value=online_apps),
        ):
            response = self.request_status()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            "status": "degraded",
            "issues": [
                "api_apps_unavailable",
                "workers_unavailable",
                "content_apps_unavailable",
            ],
        })

    def test_failed_status_reports_database_issue(self):
        with (
            patch.object(PulpStatusView, "_get_db_conn_status", return_value=False),
            patch.object(PulpStatusView, "_get_redis_conn_status") as redis_status,
            patch.object(AppStatus.objects, "online") as online_apps,
        ):
            response = self.request_status()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {
            "status": "failed",
            "issues": ["database_unavailable"],
        })
        redis_status.assert_not_called()
        online_apps.assert_not_called()

    def test_app_status_check_exception_has_distinct_issue(self):
        with (
            patch.object(PulpStatusView, "_get_db_conn_status", return_value=True),
            patch.object(PulpStatusView, "_get_redis_conn_status", return_value=True),
            patch.object(AppStatus.objects, "online", side_effect=RuntimeError("query failed")),
        ):
            response = self.request_status()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, {
            "status": "failed",
            "issues": ["app_status_check_failed"],
        })
