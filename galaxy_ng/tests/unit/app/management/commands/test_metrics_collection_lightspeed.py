from unittest.mock import patch, mock_open, MagicMock
from django.core.management import call_command
from django.test import TransactionTestCase
import os

s3_details = {
    "aws_access_key_id": "blah",
    "aws_secret_access_key": "blah",
    "aws_region": "blah",
    "aws_bucket": "blah",
}


class TestMetricsCollectionLightspeedCommand(TransactionTestCase):
    """Tests for the metrics-collection-lightspeed management command.

    Uses TransactionTestCase because the command runs raw SQL COPY queries
    against database tables (ansible_collection, core_content, etc.) that
    require actual database access outside of a transaction wrapper.
    """

    # Avoid reset_sequences which can cause issues with signal handlers
    reset_sequences = False

    def setUp(self):
        super().setUp()
        self.api_status_patch = patch('galaxy_ng.app.metrics_collection.common_data.api_status')
        self.api_status = self.api_status_patch.start()
        self.api_status.return_value = {}

    def tearDown(self):
        self.api_status_patch.stop()

    def _fixture_teardown(self):
        # Override to avoid calling flush which triggers post_migrate signals
        # that fail with _populate_access_policies() missing 'apps' argument.
        # Since we're not creating test data, we don't need to flush.
        pass

    def test_command_output(self):
        call_command("metrics-collection-lightspeed")

    @patch("galaxy_ng.app.metrics_collection.lightspeed.data._get_csv_splitter")
    @patch("builtins.open", new_callable=mock_open, read_data="data")
    @patch("boto3.client")
    @patch.dict(os.environ, s3_details, clear=True)
    def test_write_file_to_s3_success(self, boto3, mock_file, simple_csv_helper):
        assert os.getenv("aws_access_key_id") == "blah"  # noqa: SIM112
        assert os.getenv("aws_secret_access_key") == "blah"  # noqa: SIM112
        assert os.getenv("aws_region") == "blah"  # noqa: SIM112
        assert os.getenv("aws_bucket") == "blah"  # noqa: SIM112

        csv_splitter = MagicMock()
        csv_splitter.write = MagicMock(name="write")
        csv_splitter.file_list = MagicMock(name="file_list")
        simple_csv_helper.return_value = csv_splitter

        call_command("metrics-collection-lightspeed")

        self.api_status.assert_called()
        simple_csv_helper.assert_called()
        csv_splitter.file_list.assert_called()
        csv_splitter.write.assert_called()
