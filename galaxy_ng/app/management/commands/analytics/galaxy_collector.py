import os
import io
import platform
import distro
from django.conf import settings

from insights_analytics_collector import CsvFileSplitter, register

from galaxy_ng.app.management.commands.analytics.collector import Collector
from galaxy_ng.app.management.commands.analytics.package import Package


@register(
    "config",
    "1.0",
    description="General platform configuration.",
    config=True
)
def config(since, **kwargs):
    # TODO:
    # license_info = get_license()
    license_info = {}

    install_type = "traditional"
    if os.environ.get("container") == "oci":
        install_type = "openshift"
    elif "KUBERNETES_SERVICE_PORT" in os.environ:
        install_type = "k8s"
    return {
        "platform": {
            "system": platform.system(),
            "dist": distro.linux_distribution(),
            "release": platform.release(),
            "type": install_type,
        },
        "install_uuid": "todo", # source.info["install_uuid"],
        "tower_url_base": "todo", # source.info["url"],
        "tower_version": "todo", # source.info["version"],
        # 'instance_uuid': settings.SYSTEM_UUID,
        "license_type": license_info.get("license_type", "UNLICENSED"),
        "free_instances": license_info.get("free_instances", 0),
        "total_licensed_instances": license_info.get("instance_count", 0),
        "license_expiry": license_info.get("time_remaining", 0),
        "authentication_backends": settings.AUTHENTICATION_BACKENDS,
        # 'pendo_tracking': settings.PENDO_TRACKING_STATE,
        # 'logging_aggregators': settings.LOG_AGGREGATOR_LOGGERS,
        # 'external_logger_enabled': settings.LOG_AGGREGATOR_ENABLED,
    }


@register(
    "instance_info",
    "1.0",
    description="Node information",
    config=True
)
def config(since, **kwargs):
    # TODO:

    return {
        "versions": {
            "system": "todo"
        },
        "online_workers": "todo",
        "online_content_apps": "todo",
        "database_connection": "todo",
        "redis_connection": "todo",
        "storage": "todo"
    }


@register(
    "ansible_collection_table",
    "1.0",
    format="csv",
    description="Data on ansible_collection"
)
def ansible_collection_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from ansible_collection) TO STDOUT WITH CSV HEADER
    """

    return _simple_csv(full_path, "ansible_collection", source_query)


@register(
    "ansible_collectionversion_table",
    "1.0",
    format="csv",
    description="Data on ansible_collectionversion"
)
def ansible_collectionversion_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from ansible_collectionversion) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "ansible_collectionversion", source_query)


@register(
    "ansible_collectionversionsignature_table",
    "1.0",
    format="csv",
    description="Data on ansible_collectionversionsignature"
)
def ansible_collectionversionsignature_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from ansible_collectionversionsignature) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "ansible_collectionversionsignature", source_query)


@register(
    "ansible_collectionimport_table",
    "1.0",
    format="csv",
    description="Data on ansible_collectionimport"
)
def ansible_collectionimport_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from ansible_collectionimport) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "ansible_collectionimport", source_query)


@register(
    "container_containerrepository_table",
    "1.0",
    format="csv",
    description="Data on container_containerrepository"
)
def container_containerrepository_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from container_containerrepository) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_containerrepository", source_query)


@register(
    "container_containerremote_table",
    "1.0",
    format="csv",
    description="Data on container_containerremote"
)
def container_containerremote_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from container_containerremote) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_containerremote", source_query)


@register(
    "container_tag_table",
    "1.0",
    format="csv",
    description="Data on container_tag"
)
def container_tag_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from container_tag) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_tag", source_query)


@register(
    "container_tag_table",
    "1.0",
    format="csv",
    description="Data on container_tag"
)
def container_tag_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * from container_tag) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_tag", source_query)












def _simple_csv(
    full_path, file_name, query, max_data_size=Package.MAX_DATA_SIZE
):
    file_path = _get_file_path(full_path, file_name)
    tfile = CsvFileSplitter(filespec=file_path, max_file_size=max_data_size)

    with Collector.db_connection().cursor() as cursor:
        cursor.copy_expert(query, tfile)

    return tfile.file_list()


def _get_file_path(path, table):
    return os.path.join(path, table + "_table.csv")


def write_file_to_s3(s3, bucket_name, source_file_path, destination_file_path):
    """
    Copies data to s3 bucket file
    """
    with open(source_file_path, "rb") as fin:
        data = io.BytesIO(fin.read())

        s3_obj = {"bucket_name": bucket_name, "key": destination_file_path}
        upload = s3.Object(**s3_obj)
        put_value = {"Body": data}

        upload.put(**put_value)

        return upload