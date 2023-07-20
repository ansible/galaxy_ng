import logging
from time import sleep

import pytest

from galaxykit.collections import get_all_collections, delete_collection
from galaxykit.groups import delete_group
from galaxykit.namespaces import get_namespace, delete_namespace
from galaxykit.users import delete_user
from ..utils import build_collection, ansible_galaxy, wait_for_url
from ..utils.iqe_utils import beta_galaxy_cleanup
from ..constants import BETA_GALAXY_PROFILES

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)
from ..utils.rbac_utils import create_test_user, upload_test_artifact
from ..utils.tools import generate_random_artifact_version

logger = logging.getLogger(__name__)


def test_community_settings(galaxy_client):
    """Tests settings are correct"""
    g_client = galaxy_client(None)

    resp = g_client.get('/api/_ui/v1/settings/')

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


def test_community_feature_flags(galaxy_client):
    """Tests feature flags are correct"""
    g_client = galaxy_client(None)
    resp = g_client.get('/api/_ui/v1/feature-flags/')
    assert resp['ai_deny_index'] is True
    assert resp['display_repositories'] is False
    assert resp['execution_environments'] is False
    assert resp['legacy_roles'] is True


def test_me_anonymous(galaxy_client):
    """Tests anonymous user is detected correctly"""

    g_client = galaxy_client(None)
    resp = g_client.get('/api/_ui/v1/me/')

    assert resp['username'] == ""
    assert resp['id'] is None
    assert resp['is_anonymous'] is True
    assert resp['is_superuser'] is False


def test_me_social(github_user_1):
    """ Tests a social authed user can see their user info """
    r = github_user_1.get("_ui/v1/me/")
    assert r['username'] == github_user_1.username


def test_me_social_with_precreated_user(galaxy_client):
    """ Make sure social auth associates to the correct username """
    gc_admin = galaxy_client("admin")
    github_user_username = BETA_GALAXY_PROFILES["github_user"]["username"]
    try:
        delete_user(gc_admin, github_user_username)
        delete_namespace(gc_admin, github_user_username.replace("-", "_"))
    except ValueError:
        pass
    create_test_user(gc_admin, github_user_username)
    gc = galaxy_client("github_user", github_social_auth=True)
    uinfo = gc.get('_ui/v1/me/')
    assert uinfo['username'] == gc.username
    beta_galaxy_cleanup(galaxy_client, "github_user")


def test_social_auth_creates_group(galaxy_client):
    gc_admin = galaxy_client("admin")
    github_user_username = BETA_GALAXY_PROFILES["github_user"]["username"]
    group = f"namespace:{github_user_username}".replace("-", "_")
    try:
        delete_user(gc_admin, github_user_username)
        delete_group(gc_admin, group)
        delete_namespace(gc_admin, github_user_username.replace("-", "_"))
    except ValueError:
        pass
    gc = galaxy_client("github_user", github_social_auth=True)
    uinfo = gc.get('_ui/v1/me/')
    assert uinfo['username'] == gc.username
    assert uinfo['groups'][0]['name'] == group


def test_social_auth_creates_v3_namespace(github_user_1, galaxy_client):
    expected_ns = f"{github_user_1.username}".replace("-", "_")
    ns = get_namespace(github_user_1, expected_ns)
    assert ns["name"] == expected_ns
    collection = upload_test_artifact(github_user_1, expected_ns)

    gc_admin = galaxy_client("admin")
    delete_collection(gc_admin, namespace=collection.namespace, collection=collection.name)
    # test with collection publish ?
    # make a collection


def test_social_auth_creates_v3_namespace_upload_cli(github_user_1, galaxy_client):
    expected_ns = f"{github_user_1.username}".replace("-", "_")
    ns = get_namespace(github_user_1, expected_ns)
    assert ns["name"] == expected_ns

    test_version = generate_random_artifact_version()
    artifact = build_collection(
        "skeleton",
        config={"namespace": expected_ns, "version": test_version, "tags": ["tools"]},
    )

    ansible_galaxy(
        f"collection publish {artifact.filename}",
        server_url=github_user_1.galaxy_root,
        force_token=True,
        token=github_user_1.get_token()
    )
    gc_admin = galaxy_client("admin")
    url = f"v3/plugin/ansible/content/" \
          f"published/collections/index/{expected_ns}/{artifact.name}/"
    wait_for_url(gc_admin, url)
    delete_collection(gc_admin, namespace=artifact.namespace, collection=artifact.name)


def test_social_auth_creates_legacynamespace(github_user_1):
    r = github_user_1.get(f"v1/namespaces/?name={github_user_1.username}")
    assert r['count'] == 1
    assert r['results'][0]['name'] == github_user_1.username
    assert r['results'][0]['summary_fields']['owners'][0]['username'] == github_user_1.username


def test_update_legacynamespace_owners(github_user_1, github_user_2):
    uinfo2 = github_user_2.get(f"_ui/v1/me/")
    ns_resp = github_user_1.get(f"v1/namespaces/?name={github_user_1.username}")
    ns_id = ns_resp['results'][0]['id']
    ns_url = f'v1/namespaces/{ns_id}/'
    owners_url = ns_url + 'owners/'
    new_owners = {'owners': [{'id': uinfo2['id']}]}
    # put the payload
    github_user_1.put(owners_url, body=new_owners)
    # get the new data
    owners2 = github_user_1.get(owners_url)
    owners2_usernames = [x['username'] for x in owners2]
    assert 'gh01' not in owners2_usernames
    assert uinfo2['username'] in owners2_usernames


def test_list_collections_anonymous(galaxy_client):
    """Tests whether collections can be browsed anonymously"""

    g_client = galaxy_client(None)
    resp = get_all_collections(g_client)
    validate_json(instance=resp, schema=schema_objectlist)


def test_list_collections_social(github_user_1):
    """ Tests a social authed user can see collections """
    resp = get_all_collections(github_user_1)
    validate_json(instance=resp, schema=schema_objectlist)
