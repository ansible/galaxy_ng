import boto3
import os

from insights_analytics_collector import Package as InsightsAnalyticsPackage


class Package(InsightsAnalyticsPackage):
    """Package is the class responsible to creating and sending of one tar.gz archive"""
    # Ansible Lightspeed was originally named as wisdom,
    # that's the reason for the content-type's name
    PAYLOAD_CONTENT_TYPE = "application/vnd.redhat.wisdom.filename+tgz"

    def _tarname_base(self):
        timestamp = self.collector.gather_until
        return f'galaxy-hub-wisdom-{timestamp.strftime("%Y-%m-%d-%H%M")}'

    def get_ingress_url(self):
        return False

    def _get_rh_user(self):
        return os.environ["aws_access_key_id"]  # noqa: SIM112

    def _get_rh_password(self):
        return os.environ["aws_secret_access_key"]  # noqa: SIM112

    def _get_rh_region(self):
        return os.environ["aws_region"]  # noqa: SIM112

    def _get_rh_bucket(self):
        return os.environ["aws_bucket"]  # noqa: SIM112

    def _get_rh_bucket_owner(self):
        return os.environ.get("aws_bucket_owner")  # noqa: SIM112

    def get_s3_configured(self):
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

            extra_args = {}
            bucket_owner = self._get_rh_bucket_owner()
            if bucket_owner:
                extra_args['ExpectedBucketOwner'] = bucket_owner

            return s3_client.upload_file(
                self.tar_path,
                self._get_rh_bucket(),
                os.path.basename(self.tar_path).split("/")[-1],
                ExtraArgs=extra_args if extra_args else None
            )
