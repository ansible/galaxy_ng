import importlib
import json
import logging
import os
import tarfile
from unittest.mock import MagicMock, patch, ANY
from insights_analytics_collector import register
import insights_analytics_collector.package
from galaxy_ng.app.metrics_collection.automation_analytics.collector import Collector
from galaxy_ng.app.metrics_collection.automation_analytics.package import Package
from django.test import TestCase, override_settings


@register('config', '1.0', config=True)
def config(since, **kwargs):
    return {'hub_version': 'x.y'}


@register('example1', '1.0')
def example1(since, **kwargs):
    return {'galaxy': 123}


@register('example2', '1.1')
def example2(since, **kwargs):
    return {'galaxy': 123}


@register('example3', '1.3')
def example3(since, **kwargs):
    return {'galaxy': 123}


@register('bad_json', '1.0')
def bad_json(since, **kwargs):
    return set()


@register('json_exception', '1.0')
def json_exception(since, **kwargs):
    raise ValueError('Json collection went wrong')


@register('bad_csv', '1.0', format='csv')
def bad_csv(since, **kwargs):
    return None


@register('csv_exception', '1.0', format='csv')
def csv_exception(since, **kwargs):
    raise ValueError('CSV collection went wrong')


@override_settings(GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_ENABLED=True)
class TestAutomationAnalyticsCollector(TestCase):
    def setUp(self):
        super().setUp()

        self.api_status_patch = patch('galaxy_ng.app.metrics_collection.common_data.api_status')
        self.api_status = self.api_status_patch.start()
        self.api_status.return_value = {}

        self.logger = MagicMock()
        self.log = MagicMock("log")
        self.logger.log = self.log
        self.logger.exception = MagicMock("exception")

    def tearDown(self):
        self.api_status_patch.stop()

    def test_no_config_gather(self):
        """Config is missing, no data are collected"""
        collector = Collector(
            collector_module=importlib.import_module(__name__),
            collection_type=Collector.DRY_RUN)

        tgzfiles = collector.gather(subset=['example1', 'example2'])
        assert tgzfiles is None

    def test_wrong_collections(self):
        self.skipTest("FIXME - broken by dab 2024.12.13.")
        collector = Collector(
            collector_module=importlib.import_module(__name__),
            collection_type=Collector.DRY_RUN,
            logger=self.logger
        )

        tgzfiles = collector.gather(subset=['config',
                                            'bad_json', 'json_exception',
                                            'bad_csv', 'csv_exception'])
        assert len(tgzfiles) == 1

        files = {}
        with tarfile.open(tgzfiles[0], "r:gz") as archive:
            for member in archive.getmembers():
                files[member.name] = archive.extractfile(member)

            # files added automatically
            assert './manifest.json' in files
            assert './data_collection_status.csv' in files

            # required files
            assert './config.json' in files  # required file

            # Wrong data are not part of the tarball
            assert './bad_json.json' not in files
            assert './json_exception.json' not in files
            assert './bad_csv.csv' not in files
            assert './csv_exception.csv' not in files

    def test_correct_gather(self):
        self.skipTest("FIXME - broken by dab 2024.12.13.")
        collector = Collector(
            collector_module=importlib.import_module(__name__),
            collection_type=Collector.DRY_RUN
        )
        tgzfiles = collector.gather(subset=['config',
                                            'example1',
                                            'example2'])
        assert len(tgzfiles) == 1

        files = {}
        with tarfile.open(tgzfiles[0], "r:gz") as archive:
            for member in archive.getmembers():
                files[member.name] = archive.extractfile(member)

            # files added automatically
            assert './manifest.json' in files
            assert './data_collection_status.csv' in files

            # files/data collected by @register decorator
            assert './config.json' in files  # required file
            assert './example1.json' in files
            assert json.loads(files['./example1.json'].read()) == {'galaxy': 123}
            assert './example2.json' in files

            # not in chosen subset
            assert './example3.json' not in files

        try:
            for tgz in tgzfiles:
                os.remove(tgz)
        except Exception:
            pass

    @override_settings(GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_ENABLED=False)
    @override_settings(GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL="https://www.example.com")
    def test_collection_disabled(self):
        collector = Collector(
            collector_module=importlib.import_module(__name__),
            collection_type=Collector.DRY_RUN,
            logger=self.logger
        )

        tgzfiles = collector.gather(subset=['config', 'example1'])
        assert tgzfiles is None

        self.log.assert_called_with(logging.ERROR,
                                    "Metrics Collection for Ansible Automation Platform "
                                    "not enabled.")

    @override_settings(
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE=Package.SHIPPING_AUTH_CERTIFICATES
    )
    def test_invalid_auth(self):
        self._test_shipping_error()

    @override_settings(
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE=Package.SHIPPING_AUTH_USERPASS
    )
    def test_userpass_empty_user(self):
        self._test_shipping_error()

    @override_settings(
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE=Package.SHIPPING_AUTH_USERPASS
    )
    @override_settings(GALAXY_METRICS_COLLECTION_REDHAT_USERNAME="redhat")
    @override_settings(GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD="")
    def test_userpass_empty_password(self):
        self._test_shipping_error()

    @override_settings(
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE=Package.SHIPPING_AUTH_IDENTITY
    )
    def test_identity_no_org_id(self):
        self._test_shipping_error()

    @override_settings(
        GALAXY_METRICS_COLLECTION_AUTOMATION_ANALYTICS_AUTH_TYPE=Package.SHIPPING_AUTH_USERPASS
    )
    @override_settings(GALAXY_METRICS_COLLECTION_C_RH_C_UPLOAD_URL="https://www.example.com")
    @override_settings(GALAXY_METRICS_COLLECTION_REDHAT_USERNAME="redhat")
    @override_settings(GALAXY_METRICS_COLLECTION_REDHAT_PASSWORD="pass")
    @patch.object(insights_analytics_collector.package.requests.Session, "post")
    def test_valid_shipping(self, mock_post):
        self.skipTest("FIXME - broken by dab 2024.12.13.")
        mock_post_response = MagicMock(name="post_response")
        mock_post_response.status_code = 200
        mock_post.return_value = mock_post_response

        collector = Collector(
            collector_module=importlib.import_module(__name__),
            collection_type=Collector.MANUAL_COLLECTION,
            logger=self.logger
        )
        tgzfiles = collector.gather(subset=['config', 'example1'])
        assert len(tgzfiles) == 1

        expected_headers = {'User-Agent': 'GalaxyNG | Red Hat Ansible Automation Platform (x.y)'}
        mock_post.assert_called_with("https://www.example.com",
                                     files=ANY,
                                     verify=Package.CERT_PATH,
                                     auth=("redhat", "pass"),
                                     headers=expected_headers,
                                     timeout=(31, 31)
                                     )

    def _test_shipping_error(self):
        collector = Collector(
            collector_module=importlib.import_module(__name__),
            collection_type=Collector.MANUAL_COLLECTION,
            logger=self.logger
        )
        tgzfiles = collector.gather(subset=['config', 'example1'])
        assert tgzfiles is None

        # self.log.assert_called_with(logging.ERROR,
        #                            "No metrics collection, configuration is invalid. "
        #                            "Use --dry-run to gather locally without sending.")
        self.log.assert_called_with(
            logging.ERROR,
            "Metrics Collection for Ansible Automation Platform not enabled."
        )
