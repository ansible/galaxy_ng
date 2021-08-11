from django.conf import settings

import boto3
import logstash_formatter
import watchtower


AWS_ACCESS_KEY_ID = settings.CLOUDWATCH_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY = settings.CLOUDWATCH_SECRET_ACCESS_KEY
AWS_REGION_NAME = settings.CLOUDWATCH_REGION_NAME

LOGGING_GROUP = settings.CLOUDWATCH_LOGGING_GROUP
LOGGING_STREAM_NAME = settings.CLOUDWATCH_LOGGING_STREAM_NAME


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
