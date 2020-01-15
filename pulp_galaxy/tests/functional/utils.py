# coding=utf-8
"""Utilities for tests for the galaxy plugin."""
from functools import partial
from unittest import SkipTest

from pulp_smash import api, selectors
from pulp_smash.pulp3.utils import (
    gen_remote,
    gen_repo,
    get_content,
    require_pulp_3,
    require_pulp_plugins,
    sync,
)

from pulp_galaxy.tests.functional.constants import (
    GALAXY_CONTENT_NAME,
    GALAXY_CONTENT_PATH,
    GALAXY_FIXTURE_URL,
    GALAXY_PUBLICATION_PATH,
    GALAXY_REMOTE_PATH,
    GALAXY_REPO_PATH,
)


def set_up_module():
    """Skip tests Pulp 3 isn't under test or if pulp_galaxy isn't installed."""
    require_pulp_3(SkipTest)
    require_pulp_plugins({"pulp_galaxy"}, SkipTest)


def gen_galaxy_remote(url=GALAXY_FIXTURE_URL, **kwargs):
    """Return a semi-random dict for use in creating a galaxy Remote.

    :param url: The URL of an external content source.
    """
    # FIXME: Add any fields specific to a galaxy remote here
    return gen_remote(url, **kwargs)


def get_galaxy_content_paths(repo, version_href=None):
    """Return the relative path of content units present in a galaxy repository.

    :param repo: A dict of information about the repository.
    :param version_href: The repository version to read.
    :returns: A dict of lists with the paths of units present in a given repository.
        Paths are given as pairs with the remote and the local version for different content types.
    """
    # FIXME: The "relative_path" is actually a file path and name
    # It's just an example -- this needs to be replaced with an implementation that works
    # for repositories of this content type.
    return {
        GALAXY_CONTENT_NAME: [
            (content_unit["relative_path"], content_unit["relative_path"])
            for content_unit in get_content(repo, version_href)[GALAXY_CONTENT_NAME]
        ],
    }


def gen_galaxy_content_attrs(artifact):
    """Generate a dict with content unit attributes.

    :param artifact: A dict of info about the artifact.
    :returns: A semi-random dict for use in creating a content unit.
    """
    # FIXME: Add content specific metadata here.
    return {"_artifact": artifact["pulp_href"]}


def populate_pulp(cfg, url=GALAXY_FIXTURE_URL):
    """Add galaxy contents to Pulp.

    :param pulp_smash.config.PulpSmashConfig: Information about a Pulp application.
    :param url: The galaxy repository URL. Defaults to
        :data:`pulp_smash.constants.GALAXY_FIXTURE_URL`
    :returns: A list of dicts, where each dict describes one galaxy content in Pulp.
    """
    client = api.Client(cfg, api.json_handler)
    remote = {}
    repo = {}
    try:
        remote.update(client.post(GALAXY_REMOTE_PATH, gen_galaxy_remote(url)))
        repo.update(client.post(GALAXY_REPO_PATH, gen_repo()))
        sync(cfg, remote, repo)
    finally:
        if remote:
            client.delete(remote["pulp_href"])
        if repo:
            client.delete(repo["pulp_href"])
    return client.get(GALAXY_CONTENT_PATH)["results"]


def publish(cfg, repo, version_href=None):
    """Publish a repository.
    :param pulp_smash.config.PulpSmashConfig cfg: Information about the Pulp
        host.
    :param repo: A dict of information about the repository.
    :param version_href: A href for the repo version to be published.
    :returns: A publication. A dict of information about the just created
        publication.
    """
    if version_href:
        body = {"repository_version": version_href}
    else:
        body = {"repository": repo["pulp_href"]}

    client = api.Client(cfg, api.json_handler)
    call_report = client.post(GALAXY_PUBLICATION_PATH, body)
    tasks = tuple(api.poll_spawned_tasks(cfg, call_report))
    return client.get(tasks[-1]["created_resources"][0])


skip_if = partial(selectors.skip_if, exc=SkipTest)  # pylint:disable=invalid-name
"""The ``@skip_if`` decorator, customized for unittest.

:func:`pulp_smash.selectors.skip_if` is test runner agnostic. This function is
identical, except that ``exc`` has been set to ``unittest.SkipTest``.
"""
