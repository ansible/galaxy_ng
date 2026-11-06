from rest_framework.test import APIRequestFactory, force_authenticate

from galaxy_ng.app.access_control.statements.legacy import LEGACY_STATEMENTS
from galaxy_ng.app.api.v1.views import LegacyRootView
from galaxy_ng.app.api.v1.viewsets.roles import LegacyRolesViewSet
from galaxy_ng.tests.unit.api.base import BaseTestCase


class TestLegacyApiAuthentication(BaseTestCase):
    def test_legacy_root_requires_authentication(self):
        request = APIRequestFactory().get("/")

        response = LegacyRootView.as_view()(request)

        self.assertEqual(response.status_code, 401)

    def test_legacy_root_allows_authenticated_users(self):
        request = APIRequestFactory().get("/")
        force_authenticate(request, user=self.user)

        response = LegacyRootView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("roles", response.data)

    def test_legacy_read_requires_authentication(self):
        read_statements = LEGACY_STATEMENTS["LegacyAccessPolicy"][0]
        request = APIRequestFactory().get('/api/v1/roles/')
        response = LegacyRolesViewSet.as_view({'get': 'list'})(request)

        self.assertEqual(read_statements["principal"], "authenticated")
        self.assertEqual(response.status_code, 401)
