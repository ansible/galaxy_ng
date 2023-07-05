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


class TestAnalyticsExportS3Command(TestCase):
    def setUp(self):
        super().setUp()

    def test_command_output(self):
        call_command("analytics-export-s3")

    @patch("galaxy_ng.app.management.commands.analytics.galaxy_collector._get_csv_splitter")
    @patch("builtins.open", new_callable=mock_open, read_data="data")
    @patch("boto3.client")
    @patch.dict(os.environ, s3_details, clear=True)
    def test_write_file_to_s3_success(self, boto3, mock_file, simpleCSVHelper):
        assert os.getenv("aws_access_key_id") == "blah"
        assert os.getenv("aws_secret_access_key") == "blah"
        assert os.getenv("aws_region") == "blah"
        assert os.getenv("aws_bucket") == "blah"

        csvsplitter = MagicMock()
        csvsplitter.write = MagicMock(name="write")
        csvsplitter.file_list = MagicMock(name="file_list")
        simpleCSVHelper.return_value = csvsplitter

        call_command("analytics-export-s3")

        simpleCSVHelper.assert_called()
        csvsplitter.file_list.assert_called()
        csvsplitter.write.assert_called()
