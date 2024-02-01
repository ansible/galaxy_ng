import logging

logger = logging.getLogger(__name__)


def test_gw(galaxy_client):
    gc = galaxy_client("admin")
    logger.debug(gc._get_server_version())

