import json
import logging
import os
import re
from unittest.mock import patch

import pytest
from orionutils.generator import build_collection, randstr
from pkg_resources import parse_version

from galaxy_ng.tests.integration.constants import USERNAME_PUBLISHER
from galaxykit.collections import upload_artifact, get_collection_from_repo, get_collection, \
    get_ui_collection
from galaxykit.utils import wait_for_task, GalaxyClientError

from ..utils import (
    CapturingGalaxyError,
    get_client,
    modify_artifact,
    set_certification,
)

from ..utils import build_collection as bc


logger = logging.getLogger(__name__)


class ErrorTestMode:
    """Represents a test scenario for publishing a collection."""

    def __init__(self, name, file, status, resp, no_filename=False, hash=True):  # noqa: A002
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
@pytest.mark.all
def test_api_publish(artifact, use_distribution, hub_version, galaxy_client):
    """Test the most basic, valid artifact upload via the API.

    Should successfully return a task URL to get updates of the progress,
    which should indicate a successful import.
    """
    gc = galaxy_client("admin")

    # inbound repos aren't created anymore. This will create one to verify that they still
    # work on legacy clients
    if use_distribution:
        if parse_version(hub_version) < parse_version('4.6'):
            pytest.skip("Hub version is 4.5")
        distros = gc.get("pulp/api/v3/distributions/"
                         "ansible/ansible/?name=inbound-{artifact.namespace}")

        if distros["count"] == 0:
            repo = gc.get("pulp/api/v3/repositories/ansible/ansible/?name=staging")["results"][0]
            try:
                r = gc.post("pulp/api/v3/distributions/ansible/ansible/", body={
                    "repository": repo["pulp_href"],
                    "name": f"inbound-{artifact.namespace}",
                    "base_path": f"inbound-{artifact.namespace}",
                })
                logger.debug("Waiting for upload to be completed")
                wait_for_task(gc, r)
            except GalaxyClientError as e:
                if "must be unique" not in e.response.text:
                    raise e

    resp = upload_artifact(None, gc, artifact, use_distribution=use_distribution)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"


@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_validated_publish(ansible_config, artifact, galaxy_client):
    """
    Publish a collection to the validated repo.
    """
    # gc = galaxy_client("partner_engineer")
    gc = galaxy_client("admin")
    logging.debug(f"artifact name {artifact.name}")
    logging.debug(f"artifact namespace {artifact.namespace}")

    resp = upload_artifact(None, gc, artifact)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "completed"

    set_certification(ansible_config(), gc, artifact, level="validated")
    collection_resp = get_collection_from_repo(gc, "validated", artifact.namespace,
                                               artifact.name, "1.0.0")
    assert collection_resp["name"] == artifact.name


@pytest.mark.skip
@pytest.mark.all
def test_api_publish_bad_hash(ansible_config, artifact, upload_artifact):
    """Test error responses when posting to the collections endpoint."""
    config = ansible_config("admin")
    api_client = get_client(config)

    with pytest.raises(CapturingGalaxyError) as excinfo:  # noqa: SIM117
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            upload_artifact(config, api_client, artifact, hash=b"000000000000000")
    resp = json.loads(excinfo.value.http_error.read())

    assert excinfo.value.http_error.status == 400, excinfo.value
    assert resp["errors"]
    assert resp["errors"][0]["status"] == "400"
    assert resp["errors"][0]["code"] == "invalid"
    assert resp["errors"][0]["detail"]


@pytest.mark.stage_health
@pytest.mark.all
def test_api_publish_invalid_tarball(artifact, galaxy_client):
    """Test error responses when uploading a file that is not a tarball."""
    gc = galaxy_client("admin")

    with open(artifact.filename, "wb") as f:
        f.write(randstr(1024).encode("utf8"))

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)

    assert resp["state"] == "failed"


def test_api_publish_missing_filename(galaxy_client, artifact):
    """Test handling of uploads missing the filename parameter."""
    gc = galaxy_client("admin")

    with pytest.raises(GalaxyClientError) as excinfo:  # noqa: SIM117
        with patch("ansible.galaxy.api.GalaxyError", CapturingGalaxyError):
            upload_artifact(None, gc, artifact, no_filename=True)

    assert excinfo.value.response.status_code == 400
    assert excinfo.value.args[0]["status"] == "400"
    assert excinfo.value.args[0]["source"] == {"parameter": "file"}
    assert excinfo.value.args[0]["code"] == "invalid"
    assert excinfo.value.args[0]["detail"]


@pytest.mark.importer
@pytest.mark.stage_health
@pytest.mark.all
def test_api_publish_broken_manifest(artifact, galaxy_client):
    """Test handling of uploads missing the collection name parameter."""
    gc = galaxy_client("admin")

    with modify_artifact(artifact) as artifact_dir:
        manifest_path = os.path.join(artifact_dir, "MANIFEST.json")
        with open(manifest_path) as fp:
            manifest = json.load(fp)
        del manifest["collection_info"]["name"]
        with open(manifest_path, "w") as fp:
            json.dump(manifest, fp)

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)

    assert resp["state"] == "failed"
    assert "Invalid collection metadata. 'name' is required" in resp["error"]["description"]


INVALID_NAMES = {
    "just_wrong": lambda s: "a-wrong-name.tar.gz",
    "underscore": lambda s: s.replace("-", "_"),
    "too_long": lambda s: s.replace(s.split('-')[1], 'nevergonnagiveyouuporhurtyo' + 'u' * 100),
}


@pytest.mark.parametrize("wrong_name", INVALID_NAMES)
@pytest.mark.all
def test_api_publish_invalid_filename(galaxy_client, artifact, wrong_name):
    """Test handling of uploads with invalid filenames."""
    gc = galaxy_client("admin")

    # use the param lambda function to alter the tarball filename ...
    wrong_name = INVALID_NAMES[wrong_name](os.path.basename(artifact.filename))
    filename = os.path.join(os.path.dirname(artifact.filename), wrong_name)
    os.rename(artifact.filename, filename)

    # need to rename so that upload_artifact() has the correct name.
    artifact.filename = filename

    # Ensure an excepton is thrown by the client lib ...
    with pytest.raises(GalaxyClientError) as excinfo:  # noqa: SIM117
        with patch("ansible.galaxy.api.GalaxyError", GalaxyClientError):
            upload_artifact(None, gc, artifact)

    assert excinfo.value.response.status_code == 400
    assert excinfo.value.args[0]["status"] == "400"
    assert excinfo.value.args[0]["source"] == {"parameter": "filename"}
    assert excinfo.value.args[0]["code"] == "invalid"
    assert excinfo.value.args[0]["detail"]


def test_api_publish_missing_file(galaxy_client, artifact):
    """Test handling of POSTs to the artifact endpoint neglecting to submit a file."""
    gc = galaxy_client("admin")
    with pytest.raises(GalaxyClientError) as excinfo:  # noqa: SIM117
        with patch("ansible.galaxy.api.GalaxyError", GalaxyClientError):
            upload_artifact(None, gc, artifact, no_file=True)

    assert excinfo.value.response.status_code == 400
    assert excinfo.value.args[0]["status"] == "400"
    assert excinfo.value.args[0]["source"] == {"parameter": "file"}
    assert excinfo.value.args[0]["code"] == "required"
    assert excinfo.value.args[0]["detail"]


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
@pytest.mark.all
def test_long_field_values(galaxy_client, field):
    """Test handling of POSTs to the artifact endpoint neglecting to submit a file."""
    gc = galaxy_client("admin")
    fieldname, fieldvalue, fieldmax = field
    artifact = build_collection(
        "skeleton", config={"namespace": USERNAME_PUBLISHER, fieldname: fieldvalue}
    )
    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == "failed"
    # Should END with an error
    assert f"must not be greater than {fieldmax} characters" in resp["error"]["description"]
    assert fieldname in resp["error"]["description"]


# FIXME(jerabekjiri): unskip when https://issues.redhat.com/browse/AAP-32675 is merged
@pytest.mark.skip_in_gw
@pytest.mark.parametrize(
    "spec",
    [
        # TODO(awcrosby): move most these to galaxy-importer unit tests
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
@pytest.mark.min_hub_version("4.6dev")
@pytest.mark.all
def test_ansible_requires(ansible_config, spec, galaxy_client,
                          skip_if_require_signature_for_approval):
    """
    Test handling of POSTs to the artifact endpoint neglecting to submit a file.

    Also verifies that the collections endpoint properly returns a `requires_ansible` field,
    and that the returned field matches the collection metadata.
    """
    # GALAXY_SIGNATURE_UPLOAD_ENABLED="false" in ephemeral env
    gc = galaxy_client("partner_engineer")
    _, requires_ansible, result = spec
    artifact = build_collection(
        "skeleton",
        config={"namespace": USERNAME_PUBLISHER},
        extra_files={"meta/runtime.yml": {"requires_ansible": requires_ansible}},
    )

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    assert resp["state"] == result

    if result == "completed":
        set_certification(ansible_config(), gc, artifact)
        collection_resp = get_collection(gc, artifact.namespace, artifact.name, "1.0.0")
        assert collection_resp["requires_ansible"] == requires_ansible
        ui_collection_resp = get_ui_collection(gc, "published", artifact.namespace,
                                               artifact.name, "1.0.0")
        assert ui_collection_resp["latest_version"]["requires_ansible"] == requires_ansible


@pytest.mark.stage_health
@pytest.mark.importer
@pytest.mark.all
def test_ansible_lint_exception(galaxy_client, hub_version):
    """
    Ensure that:
        * ansible-lint runs against our uploaded collection
        * the bug in https://github.com/ansible/galaxy-importer/pull/115 remains fixed.
    """
    gc = galaxy_client("admin")

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

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)

    log_messages = [item["message"] for item in resp["messages"]]

    pattern = "Linting collection via ansible-lint"
    linting_re = re.compile(pattern)
    linting = [item for item in log_messages if linting_re.match(item)]
    assert len(linting) == 1  # linting occurred

    # ansible-lint stderr has a variety of unstructured output, most of which
    # is not expected to be logged by galaxy-importer.
    # Only stderr lines starting with CRITICAL or ERROR are logged
    stderr_msg_re = re.compile("errors were encountered during the plugin load")
    stderr_msg = [item for item in log_messages if stderr_msg_re.match(item)]
    assert len(stderr_msg) == 0  # this stderr message not in log


@pytest.mark.min_hub_version("4.8dev")
@pytest.mark.stage_health
@pytest.mark.importer
@pytest.mark.all
def test_ansible_lint_exception_AAH_2606(galaxy_client, hub_version):
    """
    https://issues.redhat.com/browse/AAH-2609
        - ansible-lint output is missing.
    """
    gc = galaxy_client("admin")

    IGNORE_CONTENT = \
        "plugins/modules/lm_otel_collector.py validate-modules:use-run-command-not-popen\n"

    expected = [

        (
            (
                "meta/runtime.yml:1: meta-runtime[unsupported-version]:"
                + " requires_ansible key must be set to a supported version."
            ),
            (
                "meta/runtime.yml:1: meta-runtime[unsupported-version]:"
                + " 'requires_ansible' key must refer to a currently supported version such as:"
            ),
        ),

        (
            "meta/runtime.yml:1: yaml[new-line-at-end-of-file]:"
            + " No new line character at the end of file"
        ),
    ]

    artifact = bc(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["database"],
        },
        extra_files={
            "meta/runtime.yml": "requires_ansible: \">=2.10\"",
            "tests/sanity/ignore-2.10.txt": IGNORE_CONTENT,
        },
    )

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)
    log_messages = [item["message"] for item in resp["messages"]]
    log_messages = "\n".join(log_messages)
    for lines in expected:
        if not isinstance(lines, tuple):
            assert lines in log_messages, log_messages
        else:
            found = False
            for line in lines:
                if line in log_messages:
                    found = True
                    break
            if not found:
                raise Exception(f"did not find any of {lines} in the log output")


@pytest.mark.importer
@pytest.mark.all
def test_api_publish_log_missing_ee_deps(galaxy_client):
    """
    Test that galaxy-importer logs when meta/execution-environment.yml
    lists a python deps file or system deps file and the listed file is not found.

    In this case a requirements.txt file exists but bindep.txt does not.
    """

    gc = galaxy_client("admin")

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

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)

    log_messages = [item["message"] for item in resp["messages"]]

    file_not_found_re = re.compile(
        r"^Error when checking meta\/execution-environment.yml for dependency files: "
        r"\[Errno 2\] No such file or directory: '\/tmp\S+bindep.txt'$"
    )
    file_not_found = [item for item in log_messages if file_not_found_re.match(item)]

    assert len(file_not_found) == 1


@pytest.mark.importer
@pytest.mark.all
def test_api_publish_ignore_files_logged(galaxy_client):
    """
    Test that galaxy-importer logs when ansible-test sanity ignore files are present.
    """
    gc = galaxy_client("admin")

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

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)

    log_messages = [item["message"] for item in resp["messages"]]

    ignorefile_re = re.compile(
        "Ignore files skip ansible-test sanity tests, found ignore-2.10.txt with 2 statement"
    )
    ignorefile = [item for item in log_messages if ignorefile_re.match(item)]

    assert len(ignorefile) == 1  # found ignorefile log message


@pytest.mark.deployment_cloud
@pytest.mark.importer
def test_publish_fail_required_tag(galaxy_client):
    """
    Test cloud publish fails when collection metadata tags do not include
    at least one tag in the galaxy-importer REQUIRED_TAG_LIST,
    as set by the galaxy-importer config CHECK_REQUIRED_TAGS.
    """
    gc = galaxy_client("basic_user")
    artifact = build_collection(
        "skeleton",
        config={
            "namespace": USERNAME_PUBLISHER,
            "tags": ["not_a_required_tag"],
        },
    )

    resp = upload_artifact(None, gc, artifact)
    resp = wait_for_task(gc, resp)

    assert resp["state"] == "failed"
    assert (
        "Invalid collection metadata. At least one tag required from tag list"
        in resp["error"]["description"]
    )
