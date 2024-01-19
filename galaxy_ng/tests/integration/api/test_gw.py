import logging
import subprocess
import tempfile
import pytest

from galaxykit import GalaxyClient
from galaxykit.collections import get_all_collections, upload_artifact
from galaxykit.namespaces import get_namespace
from galaxykit.users import get_me
from galaxykit.utils import wait_for_task
from ..utils import ansible_galaxy, wait_for_url, CollectionInspector
from ..constants import GALAXY_STAGE_ANSIBLE_PROFILES

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)
from ..utils.iqe_utils import galaxy_stage_ansible_user_cleanup, get_ansible_config
from ..utils.rbac_utils import create_test_user

logger = logging.getLogger(__name__)


def test_gw(galaxy_client):
    gc = galaxy_client("admin")
    logger.debug(gc._get_server_version())

