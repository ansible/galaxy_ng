import logging

from orionutils.generator import build_collection

from galaxy_ng.tests.integration.utils.rbac_utils import upload_test_artifact
from galaxy_ng.tests.integration.utils.tools import generate_random_string
from galaxykit.namespaces import create_namespace
from galaxykit.repositories import (
    create_repository,
    create_distribution,
    search_collection,
)
from galaxykit.utils import wait_for_task

logger = logging.getLogger(__name__)


def repo_exists(name, repo_list):
    for repo in repo_list:
        if repo["name"] == name:
            return True
    return False


def create_repo_and_dist(
    client, repo_name, hide_from_search=False, private=False, pipeline=None, remote=None
):
    logger.debug(f"creating repo {repo_name}")
    repo_res = create_repository(
        client,
        repo_name,
        hide_from_search=hide_from_search,
        private=private,
        pipeline=pipeline,
        remote=remote,
    )
    create_distribution(client, repo_name, repo_res["pulp_href"])
    return repo_res["pulp_href"]


def edit_results_for_verification(results):
    _results = results["data"]
    new_results = []
    for data in _results:
        repo_name = data["repository"]["name"]
        cv_name = data["collection_version"]["name"]
        cv_version = data["collection_version"]["version"]
        is_highest = data["is_highest"]
        is_deprecated = data["is_deprecated"]
        is_signed = data["is_signed"]
        new_result = {
            "repo_name": repo_name,
            "cv_name": cv_name,
            "cv_version": cv_version,
            "is_highest": is_highest,
            "is_deprecated": is_deprecated,
            "is_signed": is_signed,
        }
        new_results.append(new_result)
    return new_results


def search_collection_endpoint(client, **params):
    result = search_collection(client, **params)
    new_results = edit_results_for_verification(result)
    return result["meta"]["count"], new_results


def create_test_namespace(gc):
    namespace_name = f"ns_test_{generate_random_string()}"
    create_namespace(gc, namespace_name, "")
    return namespace_name


def upload_new_artifact(
    gc, namespace, repository, version, key=None, tags=None, dependencies=None, direct_upload=False
):
    artifact = build_collection(
        "skeleton",
        config={
            "namespace": namespace,
            "version": version,
            "repository_name": repository,
            "tags": tags,
            "dependencies": dependencies,
        },
        key=key,
    )
    upload_test_artifact(gc, namespace, repository, artifact, direct_upload)
    return artifact


def add_content_units(gc, content_units, repo_pulp_href):
    payload = {"add_content_units": content_units}
    resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
    wait_for_task(gc, resp_task)


def remove_content_units(gc, content_units, repo_pulp_href):
    payload = {"remove_content_units": content_units}
    resp_task = gc.post(f"{repo_pulp_href}modify/", body=payload)
    wait_for_task(gc, resp_task)


def verify_repo_data(expected_repos, actual_repos):
    def is_dict_included(dict1, dict2):
        # Check if all key-value pairs in dict1 are present in dict2
        for key, value in dict1.items():
            if key not in dict2 or dict2[key] != value:
                return False
        return True

    for expected_repo in expected_repos:
        found = False
        for actual_repo in actual_repos:
            if is_dict_included(expected_repo, actual_repo):
                found = True
        if not found:
            logger.debug(f"{expected_repo} not found in actual repos")
            return False
    return True
