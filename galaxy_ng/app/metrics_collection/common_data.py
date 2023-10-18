import os
import requests
import logging
from urllib.parse import urljoin
import platform
import distro
from django.conf import settings
from pulpcore.plugin.models import system_id

logger = logging.getLogger("metrics_collection.export_data")


def api_status():
    status_path = 'pulp/api/v3/status/'
    try:
        path = os.path.join(settings.GALAXY_API_PATH_PREFIX or '', status_path)
        url = urljoin(settings.ANSIBLE_API_HOSTNAME, path)
        response = requests.request("GET", url)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"export metrics_collection: failed API call {status_path}: "
                         f"HTTP status {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"export metrics_collection: failed API call {status_path}: {e}")
        return {}


def hub_version():
    status = api_status()
    galaxy_version = ''
    for version in status['versions']:
        if version['component'] == 'galaxy':
            galaxy_version = version['version']
    return galaxy_version


def config():

    return {
        "platform": {
            "system": platform.system(),
            "dist": distro.linux_distribution(),
            "release": platform.release(),
            "type": "openshift",  # valid for GalaxyNG/Cloud Hub
        },
        "authentication_backends": settings.AUTHENTICATION_BACKENDS,
        "deployment_mode": settings.GALAXY_DEPLOYMENT_MODE,
        "install_uuid": system_id(),  # core_systemid.pulp_id
        "instance_uuid": "",  # instances in cluster not distinguished
        "hub_url_base": settings.ANSIBLE_API_HOSTNAME,
        "hub_version": hub_version()
    }


def instance_info():
    status = api_status()

    return {
        "versions": status.get('versions', {}),
        "online_workers": status.get('online_workers', []),
        "online_content_apps": status.get('online_content_apps', []),
        "database_connection": status.get('database_connection', {}),
        "redis_connection": status.get('redis_connection', {}),
        "storage": status.get('storage', {}),
        "content_settings": status.get('content_settings', {}),
        "domain_enabled": status.get('domain_enabled', '')
    }


def collections_query():
    return """
        SELECT "ansible_collection"."pulp_id" AS uuid,
               "ansible_collection"."pulp_created",
               "ansible_collection"."pulp_last_updated",
               "ansible_collection"."namespace",
               "ansible_collection"."name"
        FROM "ansible_collection"
    """


def collection_versions_query():
    return """
        SELECT "ansible_collectionversion"."content_ptr_id" AS uuid,
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
               "ansible_collectionversion"."repository"
        FROM "ansible_collectionversion"
        INNER JOIN "core_content" ON (
            "ansible_collectionversion"."content_ptr_id" = "core_content"."pulp_id"
            )
    """


def collection_version_tags_query():
    return """
        SELECT id,
               collectionversion_id AS collection_version_id,
               tag_id
        FROM ansible_collectionversion_tags
    """


def collection_tags_query():
    return """
            SELECT pulp_id AS uuid,
                   pulp_created,
                   pulp_last_updated,
                   name
            FROM ansible_tag
    """


def collection_version_signatures_query():
    return """
        SELECT "ansible_collectionversionsignature".content_ptr_id AS uuid,
               "core_content".pulp_created,
               "core_content".pulp_last_updated,
               "ansible_collectionversionsignature".signed_collection_id AS collection_version_id,
               "ansible_collectionversionsignature".data,
               "ansible_collectionversionsignature".digest,
               "ansible_collectionversionsignature".pubkey_fingerprint,
               "ansible_collectionversionsignature".signing_service_id
        FROM ansible_collectionversionsignature
        INNER JOIN core_content
            ON core_content.pulp_id = "ansible_collectionversionsignature".content_ptr_id
    """


def signing_services_query():
    return """
        SELECT pulp_id AS uuid,
               pulp_created,
               pulp_last_updated,
               public_key,
               name
        FROM core_signingservice
    """


def collection_downloads_query():
    return """
        SELECT pulp_id AS uuid,
               pulp_created,
               pulp_last_updated,
               content_unit_id AS collection_version_id,
               ip,
               extra_data->>'org_id' AS org_id,
               user_agent
        FROM ansible_downloadlog
    """


def collection_download_counts_query():
    return """
        SELECT pulp_id AS uuid,
               pulp_created,
               pulp_last_updated,
               namespace,
               name,
               download_count
        FROM ansible_collectiondownloadcount
    """
