import glob
import logging
import os
import re
import subprocess
import sys

import requests


LOG = logging.getLogger()


NO_ISSUE = "No-Issue"
ISSUE_LABELS = [
    "Closes-Bug",
    "Closes-Issue",
    "Partial-Bug",
    "Partial-Issue",
    "Implements",
    "Partial-Implements",
    "Issue",
    "Partial-Issue",
    # ChangeLog record not required
    "Related",
    "Related-Bug",
    "Related-Issue",
]
CHANGELOG_REQUIRED_LABELS = set(ISSUE_LABELS) - {
    "Related",
    "Related-Bug",
    "Related-Issue",
}

NO_ISSUE_REGEX = re.compile(r"^\s*{}\s*$".format(NO_ISSUE), re.MULTILINE)
ISSUE_LABEL_REGEX = re.compile(
    r"^\s*({}):\s+AAH-(\d+)\s*$".format("|".join(ISSUE_LABELS)), re.MULTILINE,
)

JIRA_URL = "https://issues.redhat.com/rest/api/latest/issue/AAH-{issue}"


def git_list_commits(commit_range):
    git_range = "..".join(commit_range)
    cmd = ["git", "rev-list", "--no-merges", git_range]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8", check=True)
    return result.stdout.strip().split("\n")


def git_commit_message(commit_sha):
    cmd = ["git", "show", "-s", "--format=%B", commit_sha]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, encoding="utf-8", check=True)
    return result.stdout


def check_changelog_record(issue):
    reconrds_count = len(glob.glob(f"CHANGES/{issue}.*"))
    if reconrds_count == 0:
        LOG.error(f"Missing change log entry for issue AAH-{issue}.")
        return False
    if reconrds_count == 1:
        return True
    LOG.error(f"Multiple change log records found for issue AAH-{issue}.")
    return False


def check_issue_exists(issue):
    response = requests.head(JIRA_URL.format(issue=issue))
    if not response.ok:
        LOG.error(f"Referenced issue AAH-{issue} not found in Jira.")
        return False
    return True


def check_commit(commit_sha):
    commit_message = git_commit_message(commit_sha)
    issue_labels = ISSUE_LABEL_REGEX.findall(commit_message)
    if not issue_labels:
        no_issue_match = NO_ISSUE_REGEX.search(commit_message)
        if not no_issue_match:
            LOG.error(f"Commit {commit_sha[:8]} has no issue attached")
            return False

    ok = True
    for label, issue in issue_labels:
        if not check_issue_exists(issue):
            ok = False
        if label in CHANGELOG_REQUIRED_LABELS and not check_changelog_record(issue):
            ok = False
    return ok


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # pull_request = os.environ["TRAVIS_PULL_REQUEST"]
    # repo_slug = os.environ["TRAVIS_REPO_SLUG"]
    commit_range = os.environ["TRAVIS_COMMIT_RANGE"].split("...")
    commit_list = git_list_commits(commit_range)

    ok = True
    for commit_sha in commit_list:
        LOG.debug(f"Checking commit {commit_sha[:8]} ...")
        if not check_commit(commit_sha):
            ok = False

    # TODO: Validate pull request message.

    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
