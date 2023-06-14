import boto3
import datetime
import os
import shutil

from insights_analytics_collector import Package as InsightsAnalyticsPackage


class S3Package(InsightsAnalyticsPackage):
    PAYLOAD_CONTENT_TYPE = "application/vnd.redhat.wisdom.filename+tgz"

    def _tarname_base(self):
        timestamp = self.collector.gather_until
        return f'galaxy-hub-wisdom-{timestamp.strftime("%Y-%m-%d-%H%M")}'

    def get_ingress_url(self):
        return False

    def _get_rh_user(self):
        return os.environ["aws_access_key_id"]

    def _get_rh_password(self):
        return os.environ["aws_secret_access_key"]

    def _get_rh_region(self):
        return os.environ["aws_region"]

    def _get_rh_bucket(self):
        return os.environ["aws_bucket"]

    def get_s3_configured():
        return True

    def shipping_auth_mode(self):
        return self.SHIPPING_AUTH_S3_USERPASS

    def ship(self):
        """
        Copies data to s3 bucket file
        """

        self.logger.debug(f"shipping analytics file: {self.tar_path}")

        with open(self.tar_path, "rb"):

            # Upload the file
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=self._get_rh_user(),
                aws_secret_access_key=self._get_rh_password(),
                region_name=self._get_rh_region(),
            )

            return s3_client.upload_file(
                self.tar_path, self._get_rh_bucket(), os.path.basename(self.tar_path).split("/")[-1]
            )


class LocalPackage(S3Package):
    """Package to disk instead of S3."""

    def ship(self):
        """The tarfile is cleaned up on exit, so we need to copy it elsewhere."""

        # this is a simple/easy place to save these. (please don't bikeshed it)
        dstdir = os.path.join("/tmp", "analytics_" + datetime.datetime.now().strftime("%Y_%m_%d"))
        if not os.path.exists(dstdir):
            os.makedirs(dstdir)
        dst = os.path.join(dstdir, os.path.basename(self.tar_path))
        shutil.copy(self.tar_path, dst)
        print(f'The exported data has been saved to: {dst}')
