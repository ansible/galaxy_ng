import logging

from galaxykit.container_images import get_container_images
from galaxykit.containerutils import ContainerClient
from galaxykit.users import get_user
from galaxykit.utils import GalaxyClientError, wait_for_task
from galaxykit.container_images import delete_container as delete_image_container
from orionutils.generator import build_collection

from galaxykit.collections import get_collection, upload_artifact

from galaxy_ng.tests.integration.utils import uuid4
from galaxy_ng.tests.integration.utils.tools import generate_random_artifact_version

logger = logging.getLogger(__name__)


def create_test_user(client):
    username = f"rbac-user-test_{uuid4()}"
    password = "p@ssword!"
    client.get_or_create_user(username, password, group=None)
    return {
        "username": username,
        "password": password,
    }


def add_new_user_to_new_group(client):
    group_name = f"rbac_test_group_{uuid4()}"
    group = client.create_group(group_name)
    user = create_test_user(client)
    client.add_user_to_group(user["username"], group["id"])
    return user, group


def collection_exists(client, namespace, collection_name, version):
    try:
        get_collection(client, namespace, collection_name, version)
        return True
    except GalaxyClientError as e:
        if e.args[0]["status"] == "404":
            return False


def create_namespace(client, group, object_roles=None):
    namespace_name = f"namespace_{uuid4()}"
    namespace_name = namespace_name.replace("-", "")
    group_name = None
    if group:
        group_name = group["name"]
    client.create_namespace(namespace_name, group_name, object_roles)
    return namespace_name


def create_local_image_container(config, client):
    """
    This method is used to create an empty container to push images later in the tests.
    To do so, an image is pushed and deleted afterwards.
    """
    container_engine = config.get("container_engine")
    unauth_ctn = ContainerClient(auth=None, engine=container_engine)
    unauth_ctn.pull_image("alpine")
    ee_name = f"ee_{uuid4()}"
    client.tag_image("alpine", ee_name + ":latest")
    client.push_image(ee_name + ":latest")
    info = get_container_images(client, ee_name)
    delete_image_container(client, ee_name, info["data"][0]["digest"])
    return ee_name


def upload_test_artifact(client, namespace):
    test_version = generate_random_artifact_version()
    artifact = build_collection(
        "skeleton",
        config={"namespace": namespace, "version": test_version},
    )
    logger.debug(f"Uploading artifact {artifact}")
    resp = upload_artifact(None, client, artifact)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(client, resp)
    assert resp["state"] == "completed"
    return artifact


def user_exists(username, client):
    try:
        get_user(client, username)
        return True
    except IndexError:
        return False
