from unittest.mock import Mock, patch
from django.test import TestCase

from galaxy_ng.app.metrics_collection.automation_analytics import data


class TestAutomationAnalyticsData(TestCase):

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.data.config')
    def test_config(self, mock_config):
        mock_config.return_value = {'test': 'config'}

        result = data.config(since=None)

        assert result == {'test': 'config'}
        mock_config.assert_called_once()

    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data.instance_info'
    )
    def test_instance_info(self, mock_instance_info):
        mock_instance_info.return_value = {'test': 'instance'}

        result = data.instance_info(since=None)

        assert result == {'test': 'instance'}
        mock_instance_info.assert_called_once()

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data.collections_query'
    )
    def test_collections(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM collections"
        mock_export.return_value = ['file1.csv', 'file2.csv']

        result = data.collections(since=None, full_path='/tmp', until=None)

        mock_query.assert_called_once()
        mock_export.assert_called_once_with('/tmp', 'collections', "SELECT * FROM collections")
        assert result == ['file1.csv', 'file2.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data'
        '.collection_versions_query'
    )
    def test_collection_versions(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM collection_versions"
        mock_export.return_value = ['versions.csv']

        result = data.collection_versions(since=None, full_path='/tmp', until=None)

        mock_query.assert_called_once()
        mock_export.assert_called_once_with(
            '/tmp', 'collection_versions', "SELECT * FROM collection_versions"
        )
        assert result == ['versions.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data'
        '.collection_version_tags_query'
    )
    def test_collection_version_tags(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM version_tags"
        mock_export.return_value = ['tags.csv']

        result = data.collection_version_tags(since=None, full_path='/tmp')

        mock_query.assert_called_once()
        mock_export.assert_called_once_with(
            '/tmp', 'collection_version_tags', "SELECT * FROM version_tags"
        )
        assert result == ['tags.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data.collection_tags_query'
    )
    def test_collection_tags(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM tags"
        mock_export.return_value = ['collection_tags.csv']

        result = data.collection_tags(since=None, full_path='/tmp')

        mock_query.assert_called_once()
        mock_export.assert_called_once_with('/tmp', 'collection_tags', "SELECT * FROM tags")
        assert result == ['collection_tags.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data'
        '.collection_version_signatures_query'
    )
    def test_collection_version_signatures(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM signatures"
        mock_export.return_value = ['signatures.csv']

        result = data.collection_version_signatures(since=None, full_path='/tmp')

        mock_query.assert_called_once()
        mock_export.assert_called_once_with(
            '/tmp', 'collection_version_signatures', "SELECT * FROM signatures"
        )
        assert result == ['signatures.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data.signing_services_query'
    )
    def test_signing_services(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM signing"
        mock_export.return_value = ['signing.csv']

        result = data.signing_services(since=None, full_path='/tmp')

        mock_query.assert_called_once()
        mock_export.assert_called_once_with('/tmp', 'signing_services', "SELECT * FROM signing")
        assert result == ['signing.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data'
        '.collection_downloads_query'
    )
    def test_collection_download_logs(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM downloads"
        mock_export.return_value = ['downloads.csv']

        result = data.collection_download_logs(since=None, full_path='/tmp', until=None)

        mock_query.assert_called_once()
        mock_export.assert_called_once_with(
            '/tmp', 'collection_download_logs', "SELECT * FROM downloads"
        )
        assert result == ['downloads.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.export_to_csv')
    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data'
        '.collection_download_counts_query'
    )
    def test_collection_download_counts(self, mock_query, mock_export):
        mock_query.return_value = "SELECT * FROM counts"
        mock_export.return_value = ['counts.csv']

        result = data.collection_download_counts(since=None, full_path='/tmp', until=None)

        mock_query.assert_called_once()
        mock_export.assert_called_once_with(
            '/tmp', 'collection_download_counts', "SELECT * FROM counts"
        )
        assert result == ['counts.csv']


class TestCSVUtilities(TestCase):

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.CsvFileSplitter')
    def test_get_csv_splitter_default_size(self, mock_splitter):
        mock_instance = Mock()
        mock_splitter.return_value = mock_instance

        result = data._get_csv_splitter('/tmp/test.csv')

        mock_splitter.assert_called_once_with(
            filespec='/tmp/test.csv', max_file_size=209715200
        )
        assert result == mock_instance

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.CsvFileSplitter')
    def test_get_csv_splitter_custom_size(self, mock_splitter):
        mock_instance = Mock()
        mock_splitter.return_value = mock_instance

        result = data._get_csv_splitter('/tmp/test.csv', max_data_size=1024)

        mock_splitter.assert_called_once_with(filespec='/tmp/test.csv', max_file_size=1024)
        assert result == mock_instance

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data._simple_csv')
    def test_export_to_csv(self, mock_simple_csv):
        mock_simple_csv.return_value = ['output.csv']
        query = "SELECT * FROM test"

        result = data.export_to_csv('/tmp', 'test_file', query)

        expected_copy_query = f"""COPY (
    {query}
    ) TO STDOUT WITH CSV HEADER
    """
        mock_simple_csv.assert_called_once_with(
            '/tmp', 'test_file', expected_copy_query, max_data_size=209715200
        )
        assert result == ['output.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data._get_file_path')
    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data._get_csv_splitter')
    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.connection')
    def test_simple_csv(self, mock_connection, mock_get_splitter, mock_get_path):
        mock_get_path.return_value = '/tmp/test.csv'
        mock_splitter = Mock()
        mock_splitter.file_list.return_value = ['test1.csv', 'test2.csv']
        mock_get_splitter.return_value = mock_splitter

        mock_cursor = Mock()
        mock_copy = Mock()
        mock_copy.read.side_effect = [b'data1', b'data2', None]
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=None)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value = mock_cursor

        result = data._simple_csv('/tmp', 'test', 'SELECT * FROM test')

        mock_get_path.assert_called_once_with('/tmp', 'test')
        mock_get_splitter.assert_called_once_with('/tmp/test.csv', 209715200)
        mock_cursor.copy.assert_called_once_with('SELECT * FROM test')
        assert mock_splitter.write.call_count == 2
        mock_splitter.write.assert_any_call('data1')
        mock_splitter.write.assert_any_call('data2')
        assert result == ['test1.csv', 'test2.csv']

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data._get_file_path')
    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data._get_csv_splitter')
    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.connection')
    def test_simple_csv_custom_size(self, mock_connection, mock_get_splitter, mock_get_path):
        mock_get_path.return_value = '/tmp/test.csv'
        mock_splitter = Mock()
        mock_splitter.file_list.return_value = ['test.csv']
        mock_get_splitter.return_value = mock_splitter

        mock_cursor = Mock()
        mock_copy = Mock()
        mock_copy.read.side_effect = [b'data', None]
        mock_copy.__enter__ = Mock(return_value=mock_copy)
        mock_copy.__exit__ = Mock(return_value=None)
        mock_cursor.copy.return_value = mock_copy
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=None)
        mock_connection.cursor.return_value = mock_cursor

        result = data._simple_csv('/tmp', 'test', 'SELECT * FROM test', max_data_size=1024)

        mock_get_splitter.assert_called_once_with('/tmp/test.csv', 1024)
        assert result == ['test.csv']

    def test_get_file_path(self):
        result = data._get_file_path('/tmp/data', 'collections')

        assert result == '/tmp/data/collections.csv'

    def test_get_file_path_with_trailing_slash(self):
        result = data._get_file_path('/tmp/data/', 'collections')

        assert result == '/tmp/data/collections.csv'

    def test_get_file_path_nested_directory(self):
        result = data._get_file_path('/home/user/data/exports', 'test_table')

        assert result == '/home/user/data/exports/test_table.csv'


class TestRegisteredFunctions(TestCase):

    def test_function_decorators_exist(self):
        # Verify that all the expected functions are properly decorated
        functions_to_check = [
            'config', 'instance_info', 'collections', 'collection_versions',
            'collection_version_tags', 'collection_tags', 'collection_version_signatures',
            'signing_services', 'collection_download_logs', 'collection_download_counts'
        ]

        for func_name in functions_to_check:
            assert hasattr(data, func_name)
            func = getattr(data, func_name)
            assert callable(func)

    @patch('galaxy_ng.app.metrics_collection.automation_analytics.data.data.config')
    def test_config_with_kwargs(self, mock_config):
        mock_config.return_value = {'test': 'config'}

        result = data.config(since=None, extra_arg='test')

        assert result == {'test': 'config'}
        mock_config.assert_called_once()

    @patch(
        'galaxy_ng.app.metrics_collection.automation_analytics.data.data.instance_info'
    )
    def test_instance_info_with_kwargs(self, mock_instance_info):
        mock_instance_info.return_value = {'test': 'instance'}

        result = data.instance_info(since=None, extra_arg='test')

        assert result == {'test': 'instance'}
        mock_instance_info.assert_called_once()
