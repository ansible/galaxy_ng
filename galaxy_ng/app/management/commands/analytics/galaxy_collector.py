import os
import platform
import distro
from django.conf import settings

from insights_analytics_collector import CsvFileSplitter, register

from galaxy_ng.app.management.commands.analytics.collector import Collector


@register("config", "1.0", description="General platform configuration.", config=True)
def config(since, **kwargs):
    # TODO: license_info = get_license()
    license_info = {}

    return {
        "platform": {
            "system": platform.system(),
            "dist": distro.linux_distribution(),
            "release": platform.release(),
            "type": "traditional",
        },
        "external_logger_enabled": "todo",
        "external_logger_type": "todo",
        "install_uuid": "todo",
        "instance_uuid": "todo",
        "tower_url_base": "todo",
        "tower_version": "todo",
        "logging_aggregators": ["todo"],
        "pendo_tracking": "todo",
        "hub_url_base": "todo",
        "hub_version": "todo",
        "license_type": license_info.get("license_type", "UNLICENSED"),
        "free_instances": license_info.get("free_instances", 0),
        "total_licensed_instances": license_info.get("instance_count", 0),
        "license_expiry": license_info.get("time_remaining", 0),
        "authentication_backends": settings.AUTHENTICATION_BACKENDS,
    }


@register("instance_info", "1.0", description="Node information", config=True)
def instance_info(since, **kwargs):
    # TODO:

    return {
        "versions": {"system": "todo"},
        "online_workers": "todo",
        "online_content_apps": "todo",
        "database_connection": "todo",
        "redis_connection": "todo",
        "storage": "todo",
    }


@register("ansible_collection_table", "1.0", format="csv", description="Data on ansible_collection")
def ansible_collection_table(since, full_path, until, **kwargs):
    source_query = """
        COPY (
            SELECT "ansible_collection"."pulp_id",
                   "ansible_collection"."pulp_created",
                   "ansible_collection"."pulp_last_updated",
                   "ansible_collection"."namespace",
                   "ansible_collection"."name"
            FROM "ansible_collection"
        )
        TO STDOUT WITH CSV HEADER
    """

    return _simple_csv(full_path, "ansible_collection", source_query)


@register(
    "ansible_collectionversion_table",
    "1.0",
    format="csv",
    description="Data on ansible_collectionversion",
)
def ansible_collectionversion_table(since, full_path, until, **kwargs):
    source_query = """COPY (
            SELECT "ansible_collectionversion"."content_ptr_id",
                   "core_content"."pulp_created",
                   "core_content"."pulp_last_updated",
                   "ansible_collectionversion"."collection_id",
                   "ansible_collectionversion"."contents",
                   "ansible_collectionversion"."dependencies",
                   "ansible_collectionversion"."description",
                   "ansible_collectionversion"."license",
                   "ansible_collectionversion"."version",
                   "ansible_collectionversion"."requires_ansible",
                   "ansible_collectionversion"."is_highest",
                   "ansible_collectionversion_tags"."tag_id"
            FROM "ansible_collectionversion"
            INNER JOIN "core_content" ON (
                "ansible_collectionversion"."content_ptr_id" = "core_content"."pulp_id"
                )
            LEFT OUTER JOIN "ansible_collectionversion_tags" ON (
                "ansible_collectionversion"."content_ptr_id" =
                "ansible_collectionversion_tags"."collectionversion_id"
                )
        ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "ansible_collectionversion", source_query)


@register(
    "ansible_collectionversionsignature_table",
    "1.0",
    format="csv",
    description="Data on ansible_collectionversionsignature",
)
def ansible_collectionversionsignature_table(since, full_path, until, **kwargs):
    # currently no rows in the table, so no objects to base a query off
    source_query = """COPY (
            SELECT * FROM ansible_collectionversionsignature
        ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "ansible_collectionversionsignature", source_query)


@register(
    "ansible_collectionimport_table",
    "1.0",
    format="csv",
    description="Data on ansible_collectionimport",
)
def ansible_collectionimport_table(since, full_path, until, **kwargs):
    # currently no rows in the table, so no objects to base a query off
    source_query = """COPY (
            SELECT * FROM ansible_collectionimport
        ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "ansible_collectionimport", source_query)


# Does not exist
# @register(
#     "ansible_collectionstats_table",
#     "1.0",
#     format="csv",
#     description="Data on ansible_collectionstats",
# )
# def ansible_collectionstats_table(since, full_path, until, **kwargs):
#     pprint.pprint("ansible_collectionstats_table")
#     source_query = """COPY (SELECT * from ansible_collectionstats) TO STDOUT WITH CSV HEADER"""
#     return _simple_csv(full_path, "ansible_collectionimport", source_query)


@register(
    "container_containerrepository_table",
    "1.0",
    format="csv",
    description="Data on container_containerrepository",
)
def container_containerrepository_table(since, full_path, until, **kwargs):
    # currently no rows in the table, so no objects to base a query off
    source_query = """COPY (
            SELECT * FROM container_containerrepository
        ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_containerrepository", source_query)


@register(
    "container_containerremote_table",
    "1.0",
    format="csv",
    description="Data on container_containerremote",
)
def container_containerremote_table(since, full_path, until, **kwargs):
    # currently no rows in the table, so no objects to base a query off
    source_query = """COPY (
            SELECT * FROM container_containerremote
        ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_containerremote", source_query)


@register("container_tag_table", "1.0", format="csv", description="Data on container_tag")
def container_tag_table(since, full_path, until, **kwargs):
    # currently no rows in the table, so no objects to base a query off
    source_query = """COPY (
            SELECT * FROM container_tag
        ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, "container_tag", source_query)


@register(
    "galaxy_legacynamespace", "1.0", format="csv", description="Data on galaxy_legacynamespace"
)
def galaxy_legacynamespace_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT
            id, created, modified, name, company, avatar_url, description, namespace_id
            FROM galaxy_legacynamespace
        ) TO STDOUT WITH CSV HEADER"""
    return _simple_csv(full_path, "galaxy_legacynamespace", source_query)


@register("galaxy_legacyrole", "1.0", format="csv", description="Data on galaxy_legacyrole")
def galaxy_legacyrole_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT
            id, created, modified, name, full_metadata, namespace_id
            FROM galaxy_legacyrole
        ) TO STDOUT WITH CSV HEADER"""
    return _simple_csv(full_path, "galaxy_legacyrole", source_query)


@register(
    "galaxy_aiindexdenylist", "1.0", format="csv", description="Data on galaxy_aiindexdenylist"
)
def galaxy_aiindexdenylist_table(since, full_path, until, **kwargs):
    source_query = """COPY (SELECT * FROM galaxy_aiindexdenylist
        ) TO STDOUT WITH CSV HEADER"""
    return _simple_csv(full_path, "galaxy_aiindexdenylist", source_query)


def _get_csv_splitter(file_path, max_data_size=209715200):
    return CsvFileSplitter(filespec=file_path, max_file_size=max_data_size)


def _simple_csv(full_path, file_name, query, max_data_size=209715200):
    file_path = _get_file_path(full_path, file_name)
    tfile = _get_csv_splitter(file_path, max_data_size)

    with Collector.db_connection().cursor() as cursor:
        with cursor.copy(query) as copy:
            while data := copy.read():
                tfile.write(str(data, 'utf8'))

    return tfile.file_list()


def _get_file_path(path, table):
    return os.path.join(path, table + "_table.csv")
