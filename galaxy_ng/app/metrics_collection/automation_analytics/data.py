import os
from django.db import connection
from insights_analytics_collector import CsvFileSplitter, register
import galaxy_ng.app.metrics_collection.common_data as data


@register("config", "1.0", description="General platform configuration.", config=True)
def config(since, **kwargs):
    return data.config()


@register("instance_info", "1.0", description="Node information")
def instance_info(since, **kwargs):
    return data.instance_info()


@register("collections", "1.0", format="csv", description="Data on ansible_collection")
def collections(since, full_path, until, **kwargs):
    query = data.collections_query()

    return export_to_csv(full_path, "collections", query)


@register(
    "collection_versions",
    "1.0",
    format="csv",
    description="Data on ansible_collectionversion",
)
def collection_versions(since, full_path, until, **kwargs):
    query = data.collection_versions_query()

    return export_to_csv(full_path, "collection_versions", query)


@register(
    "collection_version_tags",
    "1.0",
    format="csv",
    description="Full sync: Data on ansible_collectionversion_tags"
)
def collection_version_tags(since, full_path, **kwargs):
    query = data.collection_version_tags_query()
    return export_to_csv(full_path, "collection_version_tags", query)


@register(
    "collection_tags",
    "1.0",
    format="csv",
    description="Data on ansible_tag"
)
def collection_tags(since, full_path, **kwargs):
    query = data.collection_tags_query()
    return export_to_csv(full_path, "collection_tags", query)


@register(
    "collection_version_signatures",
    "1.0",
    format="csv",
    description="Data on ansible_collectionversionsignature",
)
def collection_version_signatures(since, full_path, **kwargs):
    query = data.collection_version_signatures_query()

    return export_to_csv(full_path, "collection_version_signatures", query)


@register(
    "signing_services",
    "1.0",
    format="csv",
    description="Data on core_signingservice"
)
def signing_services(since, full_path, **kwargs):
    query = data.signing_services_query()
    return export_to_csv(full_path, "signing_services", query)


# @register(
#     "collection_imports",
#     "1.0",
#     format="csv",
#     description="Data on ansible_collectionimport",
# )
# def collection_imports(since, full_path, until, **kwargs):
#     # currently no rows in the table, so no objects to base a query off
#     source_query = """COPY (
#             SELECT * FROM ansible_collectionimport
#         ) TO STDOUT WITH CSV HEADER
#     """
#     return _simple_csv(full_path, "ansible_collectionimport", source_query)
#

@register(
    "collection_download_logs",
    "1.0",
    format="csv",
    description="Data from ansible_downloadlog"
)
def collection_download_logs(since, full_path, until, **kwargs):
    query = data.collection_downloads_query()
    return export_to_csv(full_path, "collection_download_logs", query)


@register(
    "collection_download_counts",
    "1.0",
    format="csv",
    description="Data from ansible_collectiondownloadcount"
)
def collection_download_counts(since, full_path, until, **kwargs):
    query = data.collection_download_counts_query()
    return export_to_csv(full_path, "collection_download_counts", query)


def _get_csv_splitter(file_path, max_data_size=209715200):
    return CsvFileSplitter(filespec=file_path, max_file_size=max_data_size)


def export_to_csv(full_path, file_name, query):
    copy_query = f"""COPY (
    {query}
    ) TO STDOUT WITH CSV HEADER
    """
    return _simple_csv(full_path, file_name, copy_query, max_data_size=209715200)


def _simple_csv(full_path, file_name, query, max_data_size=209715200):
    file_path = _get_file_path(full_path, file_name)
    tfile = _get_csv_splitter(file_path, max_data_size)

    with connection.cursor() as cursor:
        with cursor.copy(query) as copy:
            while data := copy.read():
                tfile.write(str(data, 'utf8'))

    return tfile.file_list()


def _get_file_path(path, table):
    return os.path.join(path, table + ".csv")
