"""Utility functions for AH tests."""
import json
import logging
import os
import re
import tarfile
import tempfile
import time
#from tkinter import W
import uuid
from contextlib import contextmanager
from functools import lru_cache
from json.decoder import JSONDecodeError
from subprocess import PIPE
from subprocess import run
from urllib.parse import urljoin

import pytest
import requests
from ansible import context
from ansible.errors import AnsibleError
from ansible.galaxy.api import GalaxyAPI
from ansible.galaxy.api import GalaxyError
from ansible.galaxy.token import BasicAuthToken
from ansible.galaxy.token import GalaxyToken
from ansible.galaxy.token import KeycloakToken

logger = logging.getLogger(__name__)

# FILENAME_INCLUDED
# FILENAME_EXCLUDED
# FILENAME_MISSING


class TaskWaitingTimeout(Exception):
    pass


class CapturingGalaxyError(Exception):
    def __init__(self, http_error, message):
        self.http_error = http_error
        self.message = message


def get_client(config, require_auth=True, request_token=True, headers=None):
    """Get an API client given a role."""
    headers = headers or {}
    server = config["url"]
    assert "200" not in server
    auth_url = config.get("auth_url")

    # force the galaxy client lib to think the ignore certs kwarg was used
    # NOTE: this does not work with 2.12+
    context.CLIARGS = {"ignore_certs": True}

    token = config.get("token") or None

    # request token implies that upstream test wants to use authentication.
    # however, some tests need to auth but send request_token=False, so this
    # kwarg is poorly named and confusing.
    if request_token:
        if token:
            # keycloak must have a unique auth url ...
            if auth_url:
                token = KeycloakToken(config["token"], auth_url=auth_url)
            else:
                token = GalaxyToken(config["token"])
        else:
            token = BasicAuthToken(config["username"], config["password"])
    else:
        if require_auth:
            token = BasicAuthToken(config["username"], config["password"])
        else:
            token = None
    client = GalaxyAPI(None, "automation_hub", url=server, token=token)
    client.validate_certs = False

    # make an api call with the upstream galaxy client lib from ansible core
    def request(url, *args, **kwargs):
        url = urljoin(server, url)

        if isinstance(kwargs.get("args"), dict):
            kwargs["args"] = json.dumps(kwargs["args"])
            headers["Content-Type"] = "application/json"

        if headers:
            if "headers" in kwargs:
                kwargs["headers"].update(headers)
            else:
                kwargs["headers"] = headers

        return client._call_galaxy(url, *args, **kwargs)

    request.config = config
    return request


def upload_artifact(
    config, client, artifact, hash=True, no_filename=False, no_file=False, use_distribution=True
):
    """
    Publishes a collection to a Galaxy server and returns the import task URI.

    :param collection_path: The path to the collection tarball to publish.
    :return: The import task URI that contains the import results.
    """
    collection_path = artifact.filename
    with open(collection_path, "rb") as collection_tar:
        data = collection_tar.read()

    def to_bytes(s, errors=None):
        return s.encode("utf8")

    boundary = "--------------------------%s" % uuid.uuid4().hex
    file_name = os.path.basename(collection_path)
    part_boundary = b"--" + to_bytes(boundary, errors="surrogate_or_strict")

    from ansible.utils.hashing import secure_hash_s
    from ansible.galaxy.api import _urljoin

    form = []

    if hash:
        if isinstance(hash, bytes):
            b_hash = hash
        else:
            from hashlib import sha256

            b_hash = to_bytes(secure_hash_s(data, sha256), errors="surrogate_or_strict")
        form.extend([part_boundary, b'Content-Disposition: form-data; name="sha256"', b_hash])

    if not no_file:
        if no_filename:
            form.extend(
                [
                    part_boundary,
                    b'Content-Disposition: file; name="file"',
                    b"Content-Type: application/octet-stream",
                ]
            )
        else:
            form.extend(
                [
                    part_boundary,
                    b'Content-Disposition: file; name="file"; filename="%s"' % to_bytes(file_name),
                    b"Content-Type: application/octet-stream",
                ]
            )
    else:
        form.append(part_boundary)

    form.extend([b"", data, b"%s--" % part_boundary])

    data = b"\r\n".join(form)

    headers = {
        "Content-type": "multipart/form-data; boundary=%s" % boundary,
        "Content-length": len(data),
    }

    n_url = ""
    if use_distribution:
        n_url = (
            _urljoin(
                config["url"],
                "content",
                f"inbound-{artifact.namespace}",
                "v3",
                "artifacts",
                "collections",
            )
            + "/"
        )
    else:
        n_url = _urljoin(config["url"], "v3", "artifacts", "collections") + "/"

    resp = client(n_url, args=data, headers=headers, method="POST", auth_required=True)

    return resp


def wait_for_task(api_client, resp, timeout=300):
    ready = False
    url = urljoin(api_client.config["url"], resp["task"])
    wait_until = time.time() + timeout
    while not ready:
        if wait_until < time.time():
            raise TaskWaitingTimeout()
        try:
            resp = api_client(url)
        except GalaxyError as e:
            if "500" not in str(e):
                raise
        else:
            ready = resp["state"] not in ("running", "waiting")
        time.sleep(5)
    return resp


@contextmanager
def modify_artifact(artifact):
    filename = artifact.filename
    with tempfile.TemporaryDirectory() as dirpath:
        # unpack
        tf = tarfile.open(filename)
        tf.extractall(dirpath)

        try:
            yield dirpath

        finally:
            # re-pack
            tf = tarfile.open(filename, "w:gz")
            for name in os.listdir(dirpath):
                tf.add(os.path.join(dirpath, name), name)
            tf.close()


def approve_collection(client, collection):
    """Approve a collection version by moving it from the staging to published repository."""
    move_collection(client, collection, "staging", "published")


def reject_collection(client, collection):
    """Reject a collection version by moving it from the staging to published repository."""
    move_collection(client, collection, "staging", "rejected")


def move_collection(client, collection, source, destination):
    """Move a collection version between repositories.

    For use in versions of the API that implement repository-based approval.
    """
    namespace = collection.namespace
    name = collection.name
    version = collection.version
    url = f"/v3/collections/{namespace}/{name}/versions/{version}/move/{source}/{destination}"
    client(url, method="PUT")


def set_certification(client, collection):
    """Moves a collection from the `staging` to the `published` repository.

    For use in instances that use repository-based certification and that
    do not have auto-certification enabled.
    """
    if client.config["use_move_endpoint"]:
        url = (
            f"v3/collections/{collection.namespace}/{collection.name}/versions/"
            f"{collection.version}/move/staging/published/"
        )
        client(url, method="POST", args=b"{}")
        # no task url in response from above request, so can't intelligently wait.
        # so we'll just sleep for 1 second and hope the certification is done by then.
        dest_url = (
            f"v3/collections/{collection.namespace}/"
            f"{collection.name}/versions/{collection.version}/"
        )

        ready = False
        timeout = 5
        while not ready:
            try:
                client(dest_url, method="GET")
                # if we aren't done publishing, GalaxyError gets thrown and we skip
                # past the below line and directly to the `except GalaxyError` line.
                ready = True
            except GalaxyError:
                time.sleep(1)
                timeout = timeout - 1
                if timeout < 0:
                    raise


def uuid4():
    """Return a random UUID4 as a string."""
    return str(uuid.uuid4())
