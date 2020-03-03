from prometheus_client import Counter


collection_import_attempts = Counter(
    "galaxy_api_collection_import_attempts",
    "count of collection import attempts"
)

collection_import_failures = Counter(
    "galaxy_api_collection_import_failures",
    "count of collection import failures"
)

collection_import_successes = Counter(
    "galaxy_api_collection_import_successes",
    "count of collections imported successfully"
)

collection_artifact_download_attempts = Counter(
    "galaxy_api_collection_artifact_download_attempts",
    "count of collection artifact download attempts"
)

collection_artifact_download_failures = Counter(
    "galaxy_api_collection_artifact_download_failures",
    "count of collection artifact download failures",
    ["status"]
)

collection_artifact_download_successes = Counter(
    "galaxy_api_collection_artifact_download_successes",
    "count of successful collection artifact downloads"
)
