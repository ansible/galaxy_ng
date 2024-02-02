"""test_collection_delete.py - Tests related to collection deletion.
"""


import pytest

from galaxykit.collections import delete_collection, get_collection
from galaxykit.utils import wait_for_task, GalaxyClientError

from ..utils import (
    get_all_collections_by_repo,
    get_all_repository_collection_versions,
)
from ..utils.iqe_utils import is_stage_environment

pytestmark = pytest.mark.qa  # noqa: F821


@pytest.mark.galaxyapi_smoke
@pytest.mark.delete
@pytest.mark.collection_delete
@pytest.mark.slow_in_cloud
@pytest.mark.all
def test_delete_collection(galaxy_client, uncertifiedv2):
    """Tests whether a collection can be deleted"""
    gc = galaxy_client("partner_engineer")
    # Enumerate published collection info ...
    collectionv1 = uncertifiedv2[0]
    cnamespace = collectionv1.namespace
    cname = collectionv1.name
    ckeys = []
    for cv in uncertifiedv2:
        ckeys.append((cv.namespace, cv.name, cv.version))

    # Try deleting the whole collection ...
    delete_collection(gc, cnamespace, cname)
    # Make sure they're all gone ...
    after = get_all_collections_by_repo(gc)
    for ckey in ckeys:
        assert ckey not in after['staging']
        assert ckey not in after['published']
        with pytest.raises(GalaxyClientError):
            get_collection(gc, cnamespace, cname, ckey[2])



@pytest.mark.galaxyapi_smoke
@pytest.mark.delete
@pytest.mark.collection_version_delete
@pytest.mark.slow_in_cloud
@pytest.mark.all
def test_delete_collection_version(galaxy_client, uncertifiedv2):
    """Tests whether a collection version can be deleted"""
    gc = galaxy_client("partner_engineer")

    cv_before = get_all_repository_collection_versions(gc)

    # Enumerate published collection info ...
    collectionv1 = uncertifiedv2[0]
    cnamespace = collectionv1.namespace
    cname = collectionv1.name

    # Delete each collection version from it's repo
    # specific href ...
    ckeys = []
    for cv in uncertifiedv2:
        ckey = (cv.namespace, cv.name, cv.version)
        ckeys.append(ckey)
        matches = []
        for k, v in cv_before.items():
            if k[1:] == ckey:
                matches.append(k)
        for rcv in matches:
            rcv_url = cv_before[rcv]['href']
            # workaround
            rcv_url = rcv_url.replace("/api/galaxy/", "/api/hub/")
            resp = gc.delete(rcv_url)
            wait_for_task(gc, resp, timeout=10000)

    # make sure the collection-versions are gone ...
    cv_after = get_all_repository_collection_versions(gc)
    for ckey in ckeys:
        matches = []
        for k, v in cv_after.items():
            if k[1:] == ckey:
                matches.append(k)
        assert len(matches) == 0
        # make sure the collection was automatically purged
        # since all of it's children were deleted ...
        with pytest.raises(GalaxyClientError):
            get_collection(gc, cnamespace, cname, ckey[2])



@pytest.mark.delete
@pytest.mark.min_hub_version("4.7dev")
@pytest.mark.all
def test_delete_default_repos(galaxy_client, uncertifiedv2):
    """Verifies that default repos cannot be deleted"""
    gc = galaxy_client("admin")
    PROTECTED_BASE_PATHS = (
        "rh-certified",
        "validated",
        "community",
        "published",
        "staging",
        "rejected",
    )

    if is_stage_environment():
        protected_base_paths_list = list(PROTECTED_BASE_PATHS)
        protected_base_paths_list.remove("rh-certified")
        PROTECTED_BASE_PATHS = tuple(protected_base_paths_list)

    # Attempt to modify default distros and delete distros and repos
    for path in PROTECTED_BASE_PATHS:
        results = gc.get(f"pulp/api/v3/distributions/ansible/ansible/?base_path={path}")
        assert results["count"] == 1

        distro = results["results"][0]
        assert distro["repository"] is not None

        try:
            # workaround
            distro["pulp_href"] = distro["pulp_href"].replace("/api/galaxy/", "/api/hub/")
            gc.delete(distro["pulp_href"])
            # This API call should fail
            assert False
        except GalaxyClientError as ge:
            assert ge.response.status_code == 403

        try:
            # workaround
            distro["repository"] = distro["repository"].replace("/api/galaxy/", "/api/hub/")
            gc.delete(distro["repository"])
            # This API call should fail
            assert False
        except GalaxyClientError as ge:
            assert ge.response.status_code == 403

        try:
            gc.put(
                distro["pulp_href"],
                body={
                    **distro,
                    "repository": None
                }
            )
            # This API call should fail
            assert False
        except GalaxyClientError as ge:
            assert ge.response.status_code == 403
