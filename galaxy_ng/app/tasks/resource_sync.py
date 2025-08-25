import logging
from django.conf import settings
from ansible_base.resource_registry.tasks.sync import SyncExecutor

logger = logging.getLogger(__name__)


def run():  # pragma: no cover
    """Start DAB Resource Sync"""
    if not getattr(settings, "RESOURCE_SERVER", None):
        logger.debug(
            "Skipping periodic resource_sync, RESOURCE_SERVER not configured"
        )
        return

    executor = SyncExecutor(retries=3)
    executor.run()
    for status, resources in executor.results.items():
        for resource in resources:
            # prints `updated: {......}`
            logger.info("%s: %s", status, resource)
    logger.info("Resource Sync Finished")
