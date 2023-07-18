import logging

import pytest

from galaxykit import GalaxyClient

from galaxykit.collections import get_all_collections, delete_collection
from galaxykit.groups import delete_group
from galaxykit.namespaces import get_namespace, delete_namespace, delete_v1_namespace
from galaxykit.users import delete_user
from galaxykit.utils import GalaxyClientError
from ..constants import BETA_GALAXY_PROFILES

from jsonschema import validate as validate_json

from ..schemas import (
    schema_objectlist,
)
from ..utils.rbac_utils import create_test_user, upload_test_artifact

logger = logging.getLogger(__name__)


@pytest.mark.skip
def test_github(galaxy_client):
    gc = galaxy_client("github_user", github_social_auth=True)
    r = gc.get("_ui/v1/me/")


@pytest.mark.skip
def test_anon():
    url = "https://beta-galaxy-stage.ansible.com/api/"
    g_client = GalaxyClient(galaxy_root=url, auth=None)
    r = g_client.get("_ui/v1/me/")
    print(r)


def test_anon_fixure(galaxy_client):
    g_client = galaxy_client(None)
    r = g_client.get("_ui/v1/me/")
    print(r)
    # cleanup(galaxy_client)


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
    # cleanup(galaxy_client)


def test_community_feature_flags(galaxy_client):
    """Tests feature flags are correct"""
    g_client = galaxy_client(None)
    resp = g_client.get('/api/_ui/v1/feature-flags/')
    assert resp['ai_deny_index'] is True
    assert resp['display_repositories'] is False
    assert resp['execution_environments'] is False
    assert resp['legacy_roles'] is True
    # cleanup(galaxy_client)


def test_me_anonymous(galaxy_client):
    """Tests anonymous user is detected correctly"""

    g_client = galaxy_client(None)
    resp = g_client.get('/api/_ui/v1/me/')

    assert resp['username'] == ""
    assert resp['id'] is None
    assert resp['is_anonymous'] is True
    assert resp['is_superuser'] is False
    # cleanup(galaxy_client)


def test_me_social(galaxy_client):
    """ Tests a social authed user can see their user info """
    gc = galaxy_client("github_user", github_social_auth=True)
    r = gc.get("_ui/v1/me/")
    assert r['username'] == gc.username
    # cleanup(galaxy_client)


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
    cleanup(galaxy_client)


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
    # somtimes this is failing, user and group are created but user is no in the group
    cleanup(galaxy_client)


def test_social_auth_creates_v3_namespace(galaxy_client):
    gc = galaxy_client("github_user", github_social_auth=True)
    expected_ns = f"{gc.username}".replace("-", "_")
    ns = get_namespace(gc, expected_ns)
    assert ns["name"] == expected_ns
    collection = upload_test_artifact(gc, expected_ns)

    gc_admin = galaxy_client("admin")
    delete_collection(gc_admin, namespace=collection.namespace, collection=collection.name)
    # test with collection publish ?
    # make a collection
    cleanup(galaxy_client)


@pytest.mark.this
def test_social_auth_creates_legacynamespace(galaxy_client):
    gc = galaxy_client("github_user", github_social_auth=True)
    r = gc.get(f"v1/namespaces/?name={gc.username}")
    assert r['count'] == 1
    assert r['results'][0]['name'] == gc.username
    assert r['results'][0]['summary_fields']['owners'][0]['username'] == gc.username
    cleanup(galaxy_client)


def test_update_legacynamespace_owners(galaxy_client):
    gc_2 = galaxy_client("github_user_alt", github_social_auth=True)
    uinfo2 = gc_2.get(f"_ui/v1/me/")

    gc = galaxy_client("github_user", github_social_auth=True)
    ns_resp = gc.get(f"v1/namespaces/?name={gc.username}")
    ns_id = ns_resp['results'][0]['id']
    ns_url = f'v1/namespaces/{ns_id}/'
    owners_url = ns_url + 'owners/'

    new_owners = {'owners': [{'id': uinfo2['id']}]}

    # put the payload
    gc.put(owners_url, body=new_owners)

    # get the new data
    owners2 = gc.get(owners_url)
    owners2_usernames = [x['username'] for x in owners2]
    assert 'gh01' not in owners2_usernames
    assert uinfo2['username'] in owners2_usernames
    cleanup(galaxy_client)


def test_list_collections_anonymous(galaxy_client):
    """Tests whether collections can be browsed anonymously"""

    g_client = galaxy_client(None)
    resp = get_all_collections(g_client)
    validate_json(instance=resp, schema=schema_objectlist)
    cleanup(galaxy_client)


def test_list_collections_social(galaxy_client):
    """ Tests a social authed user can see collections """
    g_client = galaxy_client("github_user", github_social_auth=True)
    resp = get_all_collections(g_client)
    validate_json(instance=resp, schema=schema_objectlist)
    cleanup(galaxy_client)


def cleanup(gc):
    gc_admin = gc("admin")
    for u in ["github_user", "github_user_alt"]:
        github_user_username = BETA_GALAXY_PROFILES[u]["username"]
        group = f"namespace:{github_user_username}".replace("-", "_")
        try:
            delete_user(gc_admin, github_user_username)
        except ValueError:
            logger.debug("DELETE USER FAILED")
        try:
            delete_group(gc_admin, group)
        except ValueError:
            logger.debug("DELETE GROUP FAILED")
        try:
            delete_namespace(gc_admin, github_user_username.replace("-", "_"))
        except GalaxyClientError:
            logger.debug("DELETE NAMESPACE FAILED")
        try:
            delete_v1_namespace(gc_admin, github_user_username)
        except ValueError:
            logger.debug("DELETE v1 NAMESPACE FAILED")

