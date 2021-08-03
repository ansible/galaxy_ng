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
    changelog_filenames = glob.glob(f"CHANGES/{issue}.*")
    if len(changelog_filenames) == 0:
        LOG.error(f"Missing change log entry for issue AAH-{issue}.")
        return False
    if len(changelog_filenames) > 1:
        LOG.error(f"Multiple change log records found for issue AAH-{issue}.")
        return False
    with open(changelog_filenames[0]) as f:
        if len(f.readlines()) != 1:
            LOG.error(f"Expected log entry for issue AAH-{issue} to be a single line.")
            return False
    return True


def check_issue_exists(issue):
    response = requests.head(JIRA_URL.format(issue=issue))
    if response.status_code == 404:
        # 200 is returned for logged in sessions
        # 401 is for not authorized access on existing issue
        # 404 is returned if issue is not found even for unlogged users.
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


def validate_push_commits(start_commit, end_commit):
    commit_list = git_list_commits([start_commit, end_commit])
    all_commits_ok = True
    for commit_sha in commit_list:
        LOG.info(f"Checking commit {commit_sha[:8]} ...")
        if not check_commit(commit_sha):
            all_commits_ok = False
            break
    return all_commits_ok


def validate_pr_commits(github_pr_commits_url):
    request = requests.get(github_pr_commits_url)
    commit_list = [c['sha'] for c in request.json()]

    at_least_one_commit_ok = False
    for commit_sha in commit_list:
        LOG.info(f"Checking commit {commit_sha[:8]} ...")
        if check_commit(commit_sha):
            at_least_one_commit_ok = True
            break
    return at_least_one_commit_ok


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    github_pr_commits_url = os.environ["GITHUB_PR_COMMITS_URL"]
    start_commit = os.environ["START_COMMIT"]
    end_commit = os.environ["END_COMMIT"]

    if github_pr_commits_url:
        is_valid = validate_pr_commits(github_pr_commits_url)
    else:
        is_valid = validate_push_commits(start_commit, end_commit)

    if is_valid:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
