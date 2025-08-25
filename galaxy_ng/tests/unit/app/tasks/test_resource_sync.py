from unittest.mock import patch, Mock
from django.test import TestCase, override_settings

from galaxy_ng.app.tasks.resource_sync import run


class TestResourceSync(TestCase):

    @override_settings(RESOURCE_SERVER=None)
    @patch('galaxy_ng.app.tasks.resource_sync.logger')
    def test_run_no_resource_server_configured(self, mock_logger):
        """Test that run() exits early when RESOURCE_SERVER is not configured"""
        run()

        mock_logger.debug.assert_called_once_with(
            "Skipping periodic resource_sync, RESOURCE_SERVER not configured"
        )

    @patch('galaxy_ng.app.tasks.resource_sync.settings')
    @patch('galaxy_ng.app.tasks.resource_sync.SyncExecutor')
    @patch('galaxy_ng.app.tasks.resource_sync.logger')
    def test_run_with_resource_server_success(
        self, mock_logger, mock_sync_executor_class, mock_settings
    ):
        """Test successful resource sync execution"""
        mock_settings.RESOURCE_SERVER = 'http://example.com'
        mock_executor = Mock()
        mock_executor.results = {
            'updated': [{'id': 1, 'name': 'resource1'}],
            'created': [{'id': 2, 'name': 'resource2'}],
        }
        mock_sync_executor_class.return_value = mock_executor

        run()

        mock_sync_executor_class.assert_called_once_with(retries=3)
        mock_executor.run.assert_called_once()

        # Verify logging for each status and resource
        mock_logger.info.assert_any_call(
            "%s: %s", 'updated', {'id': 1, 'name': 'resource1'}
        )
        mock_logger.info.assert_any_call(
            "%s: %s", 'created', {'id': 2, 'name': 'resource2'}
        )
        mock_logger.info.assert_any_call("Resource Sync Finished")

    @patch('galaxy_ng.app.tasks.resource_sync.settings')
    @patch('galaxy_ng.app.tasks.resource_sync.SyncExecutor')
    @patch('galaxy_ng.app.tasks.resource_sync.logger')
    def test_run_with_empty_results(
        self, mock_logger, mock_sync_executor_class, mock_settings
    ):
        """Test resource sync with empty results"""
        mock_settings.RESOURCE_SERVER = 'http://example.com'
        mock_executor = Mock()
        mock_executor.results = {}
        mock_sync_executor_class.return_value = mock_executor

        run()

        mock_sync_executor_class.assert_called_once_with(retries=3)
        mock_executor.run.assert_called_once()

        # Should only log the finish message
        mock_logger.info.assert_called_once_with("Resource Sync Finished")

    @patch('galaxy_ng.app.tasks.resource_sync.settings')
    @patch('galaxy_ng.app.tasks.resource_sync.SyncExecutor')
    @patch('galaxy_ng.app.tasks.resource_sync.logger')
    def test_run_with_multiple_resources_per_status(
        self, mock_logger, mock_sync_executor_class, mock_settings
    ):
        """Test resource sync with multiple resources per status"""
        mock_settings.RESOURCE_SERVER = 'http://example.com'
        mock_executor = Mock()
        mock_executor.results = {
            'updated': [
                {'id': 1, 'name': 'resource1'},
                {'id': 2, 'name': 'resource2'},
            ],
            'deleted': [
                {'id': 3, 'name': 'resource3'},
            ]
        }
        mock_sync_executor_class.return_value = mock_executor

        run()

        # Verify all resources are logged
        mock_logger.info.assert_any_call(
            "%s: %s", 'updated', {'id': 1, 'name': 'resource1'}
        )
        mock_logger.info.assert_any_call(
            "%s: %s", 'updated', {'id': 2, 'name': 'resource2'}
        )
        mock_logger.info.assert_any_call(
            "%s: %s", 'deleted', {'id': 3, 'name': 'resource3'}
        )
        mock_logger.info.assert_any_call("Resource Sync Finished")

        # Verify total call count
        self.assertEqual(mock_logger.info.call_count, 4)
