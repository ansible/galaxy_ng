import logging
from collections import defaultdict
from json.decoder import JSONDecodeError

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations
from django.db.models import Q


logger = logging.getLogger(__name__)

# Vendored from pulp_container 2.26.15
# pulp_container/app/management/commands/container-handle-image-data.py
# Orchestration logic vendored from pulp_container 2.26.15
# pulp_container/app/management/commands/container-handle-image-data.py
# Model methods (init_metadata, etc.) still call the live Manifest API.
# Elidable — will be removed on squashmigrations.

MANIFEST_V1 = "application/vnd.docker.distribution.manifest.v1+json"
MANIFEST_LIST = "application/vnd.docker.distribution.manifest.list.v2+json"
INDEX_OCI = "application/vnd.oci.image.index.v1+json"
MANIFEST_V2 = "application/vnd.docker.distribution.manifest.v2+json"
SKIP_MEDIA_TYPES = [MANIFEST_LIST, INDEX_OCI, MANIFEST_V1]


def _get_content_data(artifact):
    from pulp_container.app.utils import get_content_data
    return get_content_data(artifact)


def _needs_os_arch_size_update(manifest):
    return manifest.media_type not in [MANIFEST_LIST, INDEX_OCI] and not (
        manifest.architecture or manifest.os or manifest.compressed_image_size
    )


def _init_manifest(manifest, broken_manifests):
    updated = False
    if not manifest.data:
        manifest_artifact = manifest._artifacts.get()
        manifest_data, raw_bytes_data = _get_content_data(manifest_artifact)
        manifest.data = raw_bytes_data.decode("utf-8")

        if not (manifest.annotations or manifest.labels or manifest.type):
            manifest.init_metadata(manifest_data)

        if _needs_os_arch_size_update(manifest):
            manifest.init_architecture_and_os()
            manifest.init_compressed_image_size()
        manifest._artifacts.clear()
        updated = True

    if not manifest.type:
        updated = manifest.init_image_nature()

    if _needs_os_arch_size_update(manifest):
        manifest.init_architecture_and_os()
        manifest.init_compressed_image_size()
        updated = True

    return updated


def _update_manifests(manifests_qs, broken_manifests):
    manifests_updated_count = 0
    manifests_to_update = []
    fields_to_update = [
        "annotations",
        "labels",
        "is_bootable",
        "is_flatpak",
        "data",
        "type",
        "os",
        "architecture",
        "compressed_image_size",
    ]

    for manifest in manifests_qs.iterator():
        try:
            needs_update = _init_manifest(manifest, broken_manifests)
        except (ObjectDoesNotExist, JSONDecodeError):
            broken_manifests.append(manifest)
            continue
        if needs_update:
            manifests_to_update.append(manifest)

        if len(manifests_to_update) > 1000:
            manifests_qs.model.objects.bulk_update(
                manifests_to_update,
                fields_to_update,
            )
            manifests_updated_count += len(manifests_to_update)
            manifests_to_update.clear()

    if manifests_to_update:
        manifests_qs.model.objects.bulk_update(
            manifests_to_update,
            fields_to_update,
        )
        manifests_updated_count += len(manifests_to_update)

    return manifests_updated_count


def handle_image_data(apps, schema_editor):
    from pulp_container.app.models import ContainerDistribution, Manifest
    from pulpcore.plugin.cache import SyncContentCache
    from pulpcore.plugin.util import get_url

    logger.info(
        "Running container-handle-image-data migration. "
        "This may take several minutes on large installations."
    )

    try:
        manifests_updated_count = 0
        broken_manifests = []

        manifests_v1 = Manifest.objects.filter(
            Q(media_type=MANIFEST_V1),
            Q(data__isnull=True)
            | Q(type__isnull=True)
            | Q(architecture__isnull=True)
            | Q(os__isnull=True)
            | Q(compressed_image_size__isnull=True),
        )
        manifests_updated_count += _update_manifests(manifests_v1, broken_manifests)

        manifests_v2 = Manifest.objects.filter(
            Q(data__isnull=True)
            | Q(annotations={}, labels={})
            | Q(type__isnull=True)
            | Q(architecture__isnull=True)
            | Q(os__isnull=True)
            | Q(compressed_image_size__isnull=True)
        )
        manifests_v2 = manifests_v2.exclude(media_type__in=SKIP_MEDIA_TYPES)
        manifests_updated_count += _update_manifests(manifests_v2, broken_manifests)

        manifest_lists = Manifest.objects.filter(
            Q(media_type__in=[MANIFEST_LIST, INDEX_OCI]),
            Q(data__isnull=True) | Q(annotations={}),
        )
        manifests_updated_count += _update_manifests(manifest_lists, broken_manifests)

        logger.info("Successfully updated %d manifests.", manifests_updated_count)

        if broken_manifests:
            logger.warning("Found %d broken manifests.", len(broken_manifests))
            broken_by_repo = defaultdict(list)
            for manifest in broken_manifests:
                repos = manifest.repositories.all()
                if repos:
                    for repo in repos:
                        broken_by_repo[get_url(repo)].append(get_url(manifest))
                else:
                    broken_by_repo["orphaned"].append(get_url(manifest))
            for repo_url, manifests in broken_by_repo.items():
                logger.warning("  %s", repo_url)
                for manifest_url in manifests:
                    logger.warning("    %s", manifest_url)

        if settings.CACHE_ENABLED and manifests_updated_count != 0:
            base_paths = ContainerDistribution.objects.values_list("base_path", flat=True)
            if base_paths:
                SyncContentCache().delete(base_key=base_paths)
            logger.info("Successfully flushed the cache.")

    except Exception:
        logger.exception(
            "Failed to run container-handle-image-data migration. "
            "Run 'pulpcore-manager container-handle-image-data' manually."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("galaxy", "0059_delete_system_auditor_role_definition"),
        ("container", "0045_alter_manifest_compressed_image_size"),
    ]

    operations = [
        migrations.RunPython(
            handle_image_data,
            reverse_code=migrations.RunPython.noop,
            elidable=True,
        ),
    ]
