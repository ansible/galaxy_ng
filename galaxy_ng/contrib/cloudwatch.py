import os

import boto3
from gunicorn import glogging
import logstash_formatter
import watchtower


AWS_ACCESS_KEY_ID = os.getenv('CW_AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('CW_AWS_SECRET_ACCESS_KEY')
AWS_REGION_NAME = os.getenv('CW_AWS_REGION_NAME')

LOGGING_GROUP = os.getenv('CW_LOGGING_GROUP')
LOGGING_STREAM_NAME = os.getenv('CW_LOGGING_STREAM_NAME')


class CloudWatchHandler(watchtower.CloudWatchLogHandler):
    """Pre-configured CloudWatch handler."""

    def __init__(self):
        boto3_session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION_NAME,
        )
        super().__init__(
            boto3_session=boto3_session,
            log_group=LOGGING_GROUP,
            stream_name=LOGGING_STREAM_NAME,
        )
        # TODO(cutwater): Request ID should not depend on Django framework
        # self.addFilter(request_id.logging.RequestIdFilter())
        self.setFormatter(logstash_formatter.LogstashFormatterV1())


class GunicornLogger(glogging.Logger):

    def setup(self, cfg):
        super().setup(cfg)

        self.error_log.addHandler(CloudWatchHandler())
        self.access_log.addHandler(CloudWatchHandler())
