import json
import logging
import os
import re
from unittest.mock import patch

import pytest
from orionutils.generator import build_collection, randstr

from galaxy_ng.tests.integration.constants import USERNAME_PUBLISHER

from ..utils import (
    CapturingGalaxyError,
    get_client,
    modify_artifact,
    set_certification,
    wait_for_task,
)

logger = logging.getLogger(__name__)


class ErrorTestMode:
    """Represents a test scenario for publishing a collection."""

    def __init__(self, name, file, status, resp, no_filename=False, hash=True):
        """Configure the test scenario.

        :param name: Name for use in the test ID.
        :param file: Optionally, a file to upload. Can be just a file, or a 2-tuple of
            filename and file.
        :param status: Expected HTTP response status code from the upload attempt.
        :param resp: Expected HTTP response JSON body.
        """

        self.name = name
        self.file = file
        self.status = status
        self.resp = resp
        self.no_filename = no_filename
        self.hash = hash


def gen_name_for_invalid():
    """Generate a filename for an artifact that is not valid."""

    key = randstr(8)
    return f"{USERNAME_PUBLISHER}-invalid{key}-1.0.0.tar.gz"


@pytest.mark.stage_health
@pytest.mark.parametrize("use_distribution", [True, False])
def test_api_publish(ansible_config, artifact, upload_artifact, use_distribution):
    """Test the most basic, valid artifact upload via the API.

    Should successfully return a task URL to get updates of the progress,
    which should indicate a successful import.
    """

    config = ansible_config("basic_user")
    api_client = get_client(config)

    with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
        try:
            resp = upload_artifact(config, api_client, artifact, use_distribution=use_distribution)
        except CapturingGalaxyError as capture:
            error_body = capture.http_error.read()
            logger.error("Upload failed with error response: %s", error_body)
            raise
        else:
            resp = wait_for_task(api_client, resp)
            assert resp["state"] == "completed"


def test_validated_publish(ansible_config, artifact, upload_artifact):
    """
    Publish a collection to the validated repo.
    """

    config = ansible_config("admin")
    api_client = get_client(config)

    with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
        try:
            resp = upload_artifact(config, api_client, artifact)
        except CapturingGalaxyError as capture:
            error_body = capture.http_error.read()
            logger.error("Upload failed with error response: %s", error_body)
            raise
        else:
            resp = wait_for_task(api_client, resp)
            assert resp["state"] == "completed"

        set_certification(api_client, artifact, level="validated")

        collection_url = (
            "/content/validated/v3/collections/"
            f"{artifact.namespace}/{artifact.name}/versions/1.0.0/"
        )
        collection_resp = api_client(collection_url)
        assert collection_resp["name"] == artifact.name


@pytest.mark.skip
def test_api_publish_bad_hash(ansible_config, artifact, upload_artifact):
    """Test error responses when posting to the collections endpoint."""
    config = ansible_config("basic_user")
    api_client = get_client(config)

    with pytest.raises(CapturingGalaxyError) as excinfo:
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            upload_artifact(config, api_client, artifact, hash=b"000000000000000")
    resp = json.loads(excinfo.value.http_error.read())

    assert excinfo.value.http_error.status == 400, excinfo.value
    assert resp["errors"]
    assert resp["errors"][0]["status"] == "400"
    assert resp["errors"][0]["code"] == "invalid"
    assert resp["errors"][0]["detail"]


@pytest.mark.stage_health
def test_api_publish_invalid_tarball(ansible_config, artifact, upload_artifact):
    """Test error responses when uploading a file that is not a tarball."""
    config = ansible_config("basic_user")
    api_client = get_client(config)

    with open(artifact.filename, "wb") as f:
        f.write(randstr(1024).encode("utf8"))

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    assert resp["state"] == "failed"


def test_api_publish_missing_filename(ansible_config, artifact, upload_artifact):
    """Test handling of uploads missing the filename parameter."""
    config = ansible_config("basic_user")
    api_client = get_client(config)

    with pytest.raises(CapturingGalaxyError) as excinfo:
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            resp = upload_artifact(config, api_client, artifact, no_filename=True)
    resp = json.loads(excinfo.value.http_error.read())

    assert excinfo.value.http_error.status == 400
    assert resp["errors"]
    assert resp["errors"][0]["status"] == "400"
    assert resp["errors"][0]["source"] == {"parameter": "file"}
    assert resp["errors"][0]["code"] == "invalid"
    assert resp["errors"][0]["detail"]


@pytest.mark.importer
@pytest.mark.stage_health
def test_api_publish_broken_manifest(ansible_config, artifact, upload_artifact):
    """Test handling of uploads missing the collection name parameter."""
    config = ansible_config("basic_user")
    api_client = get_client(config)

    with modify_artifact(artifact) as artifact_dir:
        manifest_path = os.path.join(artifact_dir, "MANIFEST.json")
        with open(manifest_path) as fp:
            manifest = json.load(fp)
        del manifest["collection_info"]["name"]
        with open(manifest_path, "w") as fp:
            json.dump(manifest, fp)

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    assert resp["state"] == "failed"
    assert "Invalid collection metadata. 'name' is required" in resp["error"]["description"]


INVALID_NAMES = {
    "just_wrong": lambda s: "a-wrong-name.tar.gz",
    "underscore": lambda s: s.replace("-", "_"),
    "too_long": lambda s: s.replace(s.split('-')[1], 'nevergonnagiveyouuporhurtyo' + 'u' * 100),
}


@pytest.mark.parametrize("wrong_name", INVALID_NAMES)
def test_api_publish_invalid_filename(ansible_config, artifact, upload_artifact, wrong_name):
    """Test handling of uploads with invalid filenames."""
    config = ansible_config("basic_user")
    api_client = get_client(config)

    # use the param lambda function to alter the tarball filename ...
    wrong_name = INVALID_NAMES[wrong_name](os.path.basename(artifact.filename))
    filename = os.path.join(os.path.dirname(artifact.filename), wrong_name)
    os.rename(artifact.filename, filename)

    # need to rename so that upload_artifact() has the correct name.
    artifact.filename = filename

    # Ensure an excepton is thrown by the client lib ...
    with pytest.raises(CapturingGalaxyError) as excinfo:
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            resp = upload_artifact(config, api_client, artifact)
    text = excinfo.value.http_error.read()
    assert excinfo.value.http_error.status == 400, f"{excinfo.value.http_error.status}: {text}"

    resp = json.loads(text)
    assert resp["errors"]
    assert resp["errors"][0]["status"] == "400"
    assert resp["errors"][0]["source"] == {"parameter": "filename"}
    assert resp["errors"][0]["detail"]
    assert resp["errors"][0]["code"] == "invalid"


def test_api_publish_missing_file(ansible_config, artifact, upload_artifact):
    """Test handling of POSTs to the artifact endpoint neglecting to submit a file."""
    config = ansible_config("basic_user")
    api_client = get_client(config)

    with pytest.raises(CapturingGalaxyError) as excinfo:
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            resp = upload_artifact(config, api_client, artifact, no_file=True)
    resp = json.loads(excinfo.value.http_error.read())

    assert excinfo.value.http_error.status == 400
    assert resp["errors"]
    assert resp["errors"][0]["status"] == "400"
    assert resp["errors"][0]["source"] == {"parameter": "file"}
    assert resp["errors"][0]["code"] == "required"
    assert resp["errors"][0]["detail"]


MAX_LENGTH_AUTHOR = 64
MAX_LENGTH_LICENSE = 32
MAX_LENGTH_NAME = 64
MAX_LENGTH_TAG = 64
MAX_LENGTH_URL = 2000
MAX_LENGTH_VERSION = 128


@pytest.mark.parametrize(
    "field",
    [
        ("authors", ["name" * (MAX_LENGTH_AUTHOR + 1)], MAX_LENGTH_AUTHOR),
        ("license", "G" * (MAX_LENGTH_LICENSE + 1), MAX_LENGTH_LICENSE),
        # ("name", "n" * (MAX_LENGTH_NAME + 1), MAX_LENGTH_NAME),
        # ("namespace", "n" * (MAX_LENGTH_NAME + 1), MAX_LENGTH_NAME),
        ("tags", ["application", "x" * (MAX_LENGTH_TAG + 1)], MAX_LENGTH_TAG),
        ("repository", "http://" + "h" * MAX_LENGTH_URL, MAX_LENGTH_URL),
        ("homepage", "http://" + "h" * MAX_LENGTH_URL, MAX_LENGTH_URL),
        ("issues", "http://" + "h" * MAX_LENGTH_URL, MAX_LENGTH_URL),
        ("documentation", "http://" + "h" * MAX_LENGTH_URL, MAX_LENGTH_URL),
        # ("version", "1.1." + "1" * MAX_LENGTH_VERSION, MAX_LENGTH_VERSION),
    ],
    ids=lambda _: _[0],
)
@pytest.mark.stage_health
@pytest.mark.importer
def test_long_field_values(ansible_config, upload_artifact, field):
    """Test handling of POSTs to the artifact endpoint neglecting to submit a file."""
    config = ansible_config("basic_user")
    api_client = get_client(config)
    fieldname, fieldvalue, fieldmax = field
    artifact = build_collection(
        "skeleton", config={"namespace": USERNAME_PUBLISHER, fieldname: fieldvalue}
    )

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    assert resp["state"] == "failed"

    # Should END with an error
    assert "must not be greater than %s characters" % fieldmax in resp["error"]["description"]
    assert fieldname in resp["error"]["description"]


@pytest.mark.parametrize(
    "spec",
    [
        # TODO: move most these to galaxy-importer unit tests
        ("2eq", "==2.10", "completed"),
        # ("gt", ">2.10.0", "completed"),
        # ("gteq", ">=2.10", "completed"),
        # ("beta", ">=2.12b1", "completed"),
        ("beta2", ">=2.12.0b1", "completed"),
        # ("lt", "<2.11", "completed"),
        # ("range1", ">=2.10,<2.11", "completed"),
        # ("it_strips_commas", ">=2.10,,", "completed"),
        # ("gtstar", ">2.10.*", "completed"),
        # ("exc", ">=2.1,!=2.1.2", "completed"),
        ("norange", "2.10", "failed"),
        # ("norange2", "2.10.0", "failed"),
        # ("norange3", "2.10.0b1", "failed"),
        # ("norange4", "2.10.*", "failed"),
        # ("1eq", "=2.10", "failed"),
        # Potentially unexpected
        # ("gt_dup", ">>>>>2.11", "completed"),
        # ("lt_dup", ">=2.10,<<2.11", "completed"),
        # ("contradiction", ">2.0,<1.0", "completed"),
        # ("text", ">nonumbers", "completed"),
    ],
    ids=lambda _: _[0],
)
@pytest.mark.importer
def test_ansible_requires(ansible_config, upload_artifact, spec):
    """
    Test handling of POSTs to the artifact endpoint neglecting to submit a file.

    Also verifies that the collections endpoint properly returns a `requires_ansible` field,
    and that the returned field matches the collection metadata.
    """
    config = ansible_config("basic_user")
    api_client = get_client(config)
    _, requires_ansible, result = spec
    artifact = build_collection(
        "skeleton",
        config={"namespace": USERNAME_PUBLISHER},
        extra_files={"meta/runtime.yml": {"requires_ansible": requires_ansible}},
    )

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    assert resp["state"] == result

    if result == "completed":
        partner_engineer_client = get_client(ansible_config("partner_engineer"))
        set_certification(partner_engineer_client, artifact)

        collection_url = f"v3/collections/{artifact.namespace}/{artifact.name}/versions/1.0.0/"
        collection_resp = api_client(collection_url)
        assert collection_resp["requires_ansible"] == requires_ansible

        ui_collection_url = (
            f"_ui/v1/repo/published/{artifact.namespace}/{artifact.name}/?versions=1.0.0"
        )
        ui_collection_resp = api_client(ui_collection_url)
        assert ui_collection_resp["latest_version"]["requires_ansible"] == requires_ansible


@pytest.mark.stage_health
@pytest.mark.importer
def test_ansible_lint_exception(ansible_config, upload_artifact):
    """
    Ensure that:
        * ansible-lint runs against our uploaded collection
        * the bug in https://github.com/ansible/galaxy-importer/pull/115 remains fixed.
    """
    config = ansible_config("basic_user")
    api_client = get_client(config)

    broken_role_yaml = [{"name": "a task", "not.a.real.module": {"fake": "fake"}}]

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["database"],
        },
        extra_files={
            "roles/main/tasks/main.yml": broken_role_yaml,
            "roles/main/README.md": "role readme",
        },
    )

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    log_messages = [item["message"] for item in resp["messages"]]

    linting_re = re.compile("Linting role .* via ansible-lint")
    critical_re = re.compile("CRITICAL Couldn't parse task at")
    linting = [item for item in log_messages if linting_re.match(item)]
    critical = [item for item in log_messages if critical_re.match(item)]

    assert len(linting) == 1  # linting occurred
    assert len(critical) == 0  # no critical errors


@pytest.mark.importer
def test_api_publish_log_missing_ee_deps(ansible_config, upload_artifact):
    """
    Test that galaxy-importer logs when meta/execution-environment.yml
    lists a python deps file or system deps file and the listed file is not found.

    In this case a requirements.txt file exists but bindep.txt does not.
    """

    config = ansible_config("basic_user")
    api_client = get_client(config)

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["cloud"],
        },
        extra_files={
            "meta/runtime.yml": {"requires_ansible": ">=2.10,<2.11"},
            "requirements.txt": ["requests  # my pypi requirement"],
            "meta/execution-environment.yml": {
                "version": "1",
                "dependencies": {"python": "requirements.txt", "system": "bindep.txt"},
            },
        },
    )

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    log_messages = [item["message"] for item in resp["messages"]]

    file_not_found_re = re.compile(
        r"^Error when checking meta\/execution-environment.yml for dependency files: "
        r"\[Errno 2\] No such file or directory: '\/tmp\S+bindep.txt'$"
    )
    file_not_found = [item for item in log_messages if file_not_found_re.match(item)]

    assert len(file_not_found) == 1


@pytest.mark.importer
def test_api_publish_ignore_files_logged(ansible_config, upload_artifact):
    """
    Test that galaxy-importer logs when ansible-test sanity ignore files are present.
    """
    config = ansible_config("basic_user")
    api_client = get_client(config)

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["networking"],
        },
        extra_files={
            "meta/runtime.yml": {"requires_ansible": ">=2.10,<2.11"},
            "tests/sanity/ignore-2.10.txt": [
                "plugins/action/ios.py action-plugin-docs",
                "plugins/modules/ios_vlan.py validate-modules:deprecation-mismatch",
            ],
        },
    )

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    log_messages = [item["message"] for item in resp["messages"]]

    ignorefile_re = re.compile(
        "Ignore files skip ansible-test sanity tests, found ignore-2.10.txt with 2 statement"
    )
    ignorefile = [item for item in log_messages if ignorefile_re.match(item)]

    assert len(ignorefile) == 1  # found ignorefile log message


@pytest.mark.cloud_only
@pytest.mark.importer
def test_publish_fail_required_tag(ansible_config, upload_artifact):
    """
    Test cloud publish fails when collection metadata tags do not include
    at least one tag in the galaxy-importer REQUIRED_TAG_LIST,
    as set by the galaxy-importer config CHECK_REQUIRED_TAGS.
    """
    config = ansible_config("basic_user")
    api_client = get_client(config)

    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["not_a_required_tag"],
        },
    )

    resp = upload_artifact(config, api_client, artifact)
    resp = wait_for_task(api_client, resp)

    assert resp["state"] == "failed"
    assert (
        "Invalid collection metadata. At least one tag required from tag list"
        in resp["error"]["description"]
    )
