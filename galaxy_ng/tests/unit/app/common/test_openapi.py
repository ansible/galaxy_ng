from unittest.mock import patch, Mock
from django.test import TestCase
from django.http import HttpResponse

from galaxy_ng.app.common.openapi import (
    preprocess_debug_logger,
    preprocess_exclude_endpoints,
    AllowCorsMiddleware
)


class TestOpenApiPreprocessors(TestCase):

    @patch('galaxy_ng.app.common.openapi.log')
    def test_preprocess_debug_logger(self, mock_log):
        endpoints = [
            ('/api/test/', 'api/test/', 'GET', 'test.views.test_view'),
            ('/api/other/', 'api/other/', 'POST', 'test.views.other_view'),
        ]
        kwargs = {'param1': 'value1', 'param2': 'value2'}

        result = preprocess_debug_logger(endpoints, **kwargs)

        # Should return the same endpoints
        result_list = list(result)
        self.assertEqual(result_list, endpoints)

        # Should log kwargs
        mock_log.debug.assert_any_call("kwargs: %s", repr(kwargs))

        # Should log each endpoint
        mock_log.debug.assert_any_call(
            'path=%s, path_regex=%s, method=%s, callback=%s',
            '/api/test/', 'api/test/', 'GET', 'test.views.test_view'
        )
        mock_log.debug.assert_any_call(
            'path=%s, path_regex=%s, method=%s, callback=%s',
            '/api/other/', 'api/other/', 'POST', 'test.views.other_view'
        )

    def test_preprocess_exclude_endpoints_include_status(self):
        endpoints = [
            ('/pulp/api/v3/status/', 'pulp/api/v3/status/', 'GET', 'status_view'),
            ('/pulp/api/v3/other/', 'pulp/api/v3/other/', 'GET', 'other_view'),
            (
                '/api/galaxy/v3/collections/',
                'api/galaxy/v3/collections/',
                'GET',
                'collections_view'
            ),
        ]

        result = preprocess_exclude_endpoints(endpoints)
        result_list = list(result)

        # Should include status endpoint and galaxy endpoints, exclude other pulp endpoints
        expected = [
            ('/pulp/api/v3/status/', 'pulp/api/v3/status/', 'GET', 'status_view'),
            (
                '/api/galaxy/v3/collections/',
                'api/galaxy/v3/collections/',
                'GET',
                'collections_view'
            ),
        ]
        self.assertEqual(result_list, expected)

    def test_preprocess_exclude_endpoints_exclude_ui(self):
        endpoints = [
            (
                '/api/galaxy/v3/collections/',
                'api/galaxy/v3/collections/',
                'GET',
                'collections_view'
            ),
            ('/api/galaxy/_ui/user/', 'api/galaxy/_ui/user/', 'GET', 'ui_user_view'),
            ('/other/api/', 'other/api/', 'GET', 'other_view'),
        ]

        result = preprocess_exclude_endpoints(endpoints)
        result_list = list(result)

        # Should exclude _ui endpoints
        expected = [
            (
                '/api/galaxy/v3/collections/',
                'api/galaxy/v3/collections/',
                'GET',
                'collections_view'
            ),
            ('/other/api/', 'other/api/', 'GET', 'other_view'),
        ]
        self.assertEqual(result_list, expected)

    def test_preprocess_exclude_endpoints_exclude_pulp(self):
        endpoints = [
            ('/pulp/api/v3/artifacts/', 'pulp/api/v3/artifacts/', 'GET', 'artifacts_view'),
            ('/pulp/api/v3/status/', 'pulp/api/v3/status/', 'GET', 'status_view'),
            (
                '/api/galaxy/v3/collections/',
                'api/galaxy/v3/collections/',
                'GET',
                'collections_view'
            ),
        ]

        result = preprocess_exclude_endpoints(endpoints)
        result_list = list(result)

        # Should exclude pulp endpoints except status
        expected = [
            ('/pulp/api/v3/status/', 'pulp/api/v3/status/', 'GET', 'status_view'),
            (
                '/api/galaxy/v3/collections/',
                'api/galaxy/v3/collections/',
                'GET',
                'collections_view'
            ),
        ]
        self.assertEqual(result_list, expected)


class TestAllowCorsMiddleware(TestCase):

    def setUp(self):
        self.get_response = Mock(return_value=HttpResponse())

    @patch('galaxy_ng.app.common.openapi.settings')
    def test_allow_cors_middleware_sets_headers(self, mock_settings):
        mock_settings.GALAXY_CORS_ALLOWED_ORIGINS = 'https://example.com'
        mock_settings.GALAXY_CORS_ALLOWED_HEADERS = 'Authorization, Content-Type'
        middleware = AllowCorsMiddleware(self.get_response)
        request = Mock()

        response = middleware(request)

        self.get_response.assert_called_once_with(request)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'https://example.com')
        self.assertEqual(response['Access-Control-Allow-Headers'], 'Authorization, Content-Type')

    def test_allow_cors_middleware_empty_settings(self):
        middleware = AllowCorsMiddleware(self.get_response)
        request = Mock()

        response = middleware(request)

        self.get_response.assert_called_once_with(request)
        self.assertEqual(response['Access-Control-Allow-Origin'], '')
        self.assertEqual(response['Access-Control-Allow-Headers'], '')

    @patch('galaxy_ng.app.common.openapi.settings')
    def test_allow_cors_middleware_wildcard_settings(self, mock_settings):
        mock_settings.GALAXY_CORS_ALLOWED_ORIGINS = '*'
        mock_settings.GALAXY_CORS_ALLOWED_HEADERS = '*'
        middleware = AllowCorsMiddleware(self.get_response)
        request = Mock()

        response = middleware(request)

        self.get_response.assert_called_once_with(request)
        self.assertEqual(response['Access-Control-Allow-Origin'], '*')
        self.assertEqual(response['Access-Control-Allow-Headers'], '*')
