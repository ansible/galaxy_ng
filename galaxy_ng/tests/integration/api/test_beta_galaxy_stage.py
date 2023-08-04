"""test_beta_galaxy.py - Tests that run against https://beta-galaxy-stage.ansible.com/
"""
import logging
import subprocess
import tempfile
import pytest

from galaxykit.collections import get_all_collections, upload_artifact
from galaxykit.namespaces import get_namespace
from galaxykit.users import get_me
from galaxykit.utils import wait_for_task
from ..utils import ansible_galaxy, wait_for_url, CollectionInspector
from ..constants import BETA_GALAXY_STAGE_PROFILES

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)
from ..utils.iqe_utils import beta_galaxy_user_cleanup
from ..utils.rbac_utils import create_test_user

logger = logging.getLogger(__name__)


@pytest.mark.beta_galaxy
def test_community_settings(galaxy_client):
    """Tests settings are correct"""
    g_client = galaxy_client(None)
    resp = g_client.get_settings()

    assert resp['GALAXY_AUTH_LDAP_ENABLED'] is None
    assert resp['GALAXY_AUTO_SIGN_COLLECTIONS'] is False
    assert resp['GALAXY_REQUIRE_CONTENT_APPROVAL'] is False
    assert resp['GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL'] is False
    assert resp['GALAXY_SIGNATURE_UPLOAD_ENABLED'] is False
    assert resp['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS'] is True
    assert resp['GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD'] is True
    assert resp['GALAXY_FEATURE_FLAGS']['display_repositories'] is False
    assert resp['GALAXY_FEATURE_FLAGS']['execution_environments'] is False
    assert resp['GALAXY_FEATURE_FLAGS']['legacy_roles'] is True
    assert resp['GALAXY_FEATURE_FLAGS']['ai_deny_index'] is True
    assert resp['GALAXY_CONTAINER_SIGNING_SERVICE'] is None


@pytest.mark.beta_galaxy
def test_community_feature_flags(galaxy_client):
    """Tests feature flags are correct"""
    g_client = galaxy_client(None)
    resp = g_client.get_feature_flags()
    assert resp['ai_deny_index'] is True
    assert resp['display_repositories'] is False
    assert resp['execution_environments'] is False
    assert resp['legacy_roles'] is True


@pytest.mark.beta_galaxy
def test_me_anonymous(galaxy_client):
    """Tests anonymous user is detected correctly"""

    g_client = galaxy_client(None)
    resp = get_me(g_client)

    assert resp['username'] == ""
    assert resp['id'] is None
    assert resp['is_anonymous'] is True
    assert resp['is_superuser'] is False


@pytest.mark.beta_galaxy
def test_me_social(gh_user_1):
    """ Tests a social authed user can see their user info """
    r = get_me(gh_user_1)
    assert r['username'] == gh_user_1.username


@pytest.mark.beta_galaxy
def test_me_social_with_precreated_user(galaxy_client):
    """ Make sure social auth associates to the correct username """
    # delete user to make sure user does not exist
    gc_admin = galaxy_client("admin")
    beta_galaxy_user_cleanup(galaxy_client, "github_user")
    github_user_username = BETA_GALAXY_STAGE_PROFILES["github_user"]["username"]
    create_test_user(gc_admin, github_user_username)
    gc = galaxy_client("github_user", github_social_auth=True, ignore_cache=True)
    uinfo = get_me(gc)
    assert uinfo['username'] == gc.username


@pytest.mark.beta_galaxy
def test_social_auth_creates_group(gh_user_1_pre):
    github_user_username = BETA_GALAXY_STAGE_PROFILES["github_user"]["username"]
    group = f"namespace:{github_user_username}".replace("-", "_")
    uinfo = get_me(gh_user_1_pre)
    assert uinfo['username'] == gh_user_1_pre.username
    assert uinfo['groups'][0]['name'] == group


@pytest.mark.beta_galaxy
def test_social_auth_creates_v3_namespace(gh_user_1_pre, generate_test_artifact):
    expected_ns = f"{gh_user_1_pre.username}".replace("-", "_")
    ns = get_namespace(gh_user_1_pre, expected_ns)
    assert ns["name"] == expected_ns
    resp = upload_artifact(None, gh_user_1_pre, generate_test_artifact)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(gh_user_1_pre, resp)
    assert resp["state"] == "completed"


@pytest.mark.beta_galaxy
def test_social_auth_creates_v3_namespace_upload_cli(gh_user_1, galaxy_client,
                                                     generate_test_artifact):
    expected_ns = f"{gh_user_1.username}".replace("-", "_")
    ns = get_namespace(gh_user_1, expected_ns)
    assert ns["name"] == expected_ns
    ansible_galaxy(
        f"collection publish {generate_test_artifact.filename}",
        server_url=gh_user_1.galaxy_root,
        force_token=True,
        token=gh_user_1.get_token()
    )
    gc_admin = galaxy_client("admin")
    url = f"v3/plugin/ansible/content/" \
          f"published/collections/index/{expected_ns}/{generate_test_artifact.name}/"
    wait_for_url(gc_admin, url)


@pytest.mark.beta_galaxy
def test_social_auth_creates_legacynamespace(gh_user_1_pre):
    r = gh_user_1_pre.get(f"v1/namespaces/?name={gh_user_1_pre.username}")
    assert r['count'] == 1
    assert r['results'][0]['name'] == gh_user_1_pre.username
    assert r['results'][0]['summary_fields']['owners'][0]['username'] == gh_user_1_pre.username


@pytest.mark.beta_galaxy
def test_update_legacynamespace_owners(gh_user_1_post, gh_user_2):
    uinfo2 = get_me(gh_user_2)
    ns_resp = gh_user_1_post.get(f"v1/namespaces/?name={gh_user_1_post.username}")
    ns_id = ns_resp['results'][0]['id']
    ns_url = f'v1/namespaces/{ns_id}/'
    owners_url = ns_url + 'owners/'
    new_owners = {'owners': [{'id': uinfo2['id']}]}
    # put the payload
    gh_user_1_post.put(owners_url, body=new_owners)
    # get the new data
    owners2 = gh_user_1_post.get(owners_url)
    owners2_usernames = [x['username'] for x in owners2]
    assert 'gh01' not in owners2_usernames
    assert uinfo2['username'] in owners2_usernames


@pytest.mark.beta_galaxy
def test_list_collections_anonymous(galaxy_client):
    """Tests whether collections can be browsed anonymously"""

    g_client = galaxy_client(None)
    resp = get_all_collections(g_client)
    validate_json(instance=resp, schema=schema_objectlist)


@pytest.mark.beta_galaxy
def test_list_collections_social(gh_user_1):
    """ Tests a social authed user can see collections """
    resp = get_all_collections(gh_user_1)
    validate_json(instance=resp, schema=schema_objectlist)


@pytest.mark.beta_galaxy
def test_social_download_artifact(gh_user_1, generate_test_artifact):
    expected_ns = f"{gh_user_1.username}".replace("-", "_")
    resp = upload_artifact(None, gh_user_1, generate_test_artifact)
    logger.debug("Waiting for upload to be completed")
    resp = wait_for_task(gh_user_1, resp)
    assert resp["state"] == "completed"

    with tempfile.TemporaryDirectory() as dir:
        filename = f"{expected_ns}-{generate_test_artifact.name}-" \
                   f"{generate_test_artifact.version}.tar.gz"
        tarball_path = f"{dir}/{filename}"
        url = f"{gh_user_1.galaxy_root}v3/plugin/" \
              f"ansible/content/published/collections/artifacts/{filename}"

        cmd = [
            "curl",
            "--retry",
            "5",
            "-L",
            "-H",
            "'Content-Type: application/json'",
            "-H",
            f"Authorization: Bearer {gh_user_1.get_token()}",
            "-o",
            tarball_path,
            url,
            "--insecure"
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        returncode = proc.wait()
        assert returncode == 0

        # Extract tarball, verify information in manifest
        ci = CollectionInspector(tarball=tarball_path)
        assert ci.namespace == expected_ns
        assert ci.name == generate_test_artifact.name
        assert ci.version == generate_test_artifact.version
