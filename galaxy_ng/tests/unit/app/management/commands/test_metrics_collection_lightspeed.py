from unittest.mock import patch, mock_open, MagicMock
from django.core.management import call_command
from django.test import TestCase
import os

s3_details = {
    "aws_access_key_id": "blah",
    "aws_secret_access_key": "blah",
    "aws_region": "blah",
    "aws_bucket": "blah",
}


class TestMetricsCollectionLightspeedCommand(TestCase):
    def setUp(self):
        super().setUp()
        self.api_status_patch = patch('galaxy_ng.app.metrics_collection.common_data.api_status')
        self.api_status = self.api_status_patch.start()
        self.api_status.return_value = {}

    def tearDown(self):
        self.api_status_patch.stop()

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
