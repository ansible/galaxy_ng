#!/usr/bin/env python3

import json
import logging
import os
import subprocess
import sys


def get_current_branch():
    pid = subprocess.run(
        'git branch --show-current',
        shell=True,
        stdout=subprocess.PIPE,
        check=True
    )
    branch_name = pid.stdout.decode('utf-8')
    branch_name = branch_name.strip()
    return branch_name


def get_changed_files(pr_branch, target_branch="master"):
    if os.environ.get('GITHUB_PR_NUMBER'):
        url = "https://patch-diff.githubusercontent.com/raw/ansible/galaxy_ng"
        url += f"/pull/{os.environ['GITHUB_PR_NUMBER']}.diff"
        print(f'GET diff from {url}')
        cmd = f'curl -s -o /tmp/pr.diff {url}'
        pid = subprocess.run(cmd, shell=True)
        assert pid.returncode == 0
        with open('/tmp/pr.diff') as f:
            raw = f.read()
        filenames = raw.split('\n')
        filenames = [x for x in filenames if x.startswith('---') or x.startswith('+++')]
        filenames = [x.split(None, 1)[1] for x in filenames if len(x.split(None, 1)) > 1]
        filenames = [x for x in filenames if not x.startswith('/dev/null')]
        filenames = [x.lstrip('a/') for x in filenames]
        filenames = [x.lstrip('b/') for x in filenames]
        filenames = sorted(set(filenames))
    else:
        # diffs the local checkout ...
        cmd = f'git diff --name-only "{pr_branch}".."{target_branch}"'
        pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, check=True)
        filenames = pid.stdout.decode('utf-8')
        filenames = filenames.split('\n')
        filenames = [x.strip() for x in filenames if x.strip()]
    return filenames


def verify_test_files_changed(changed_files):

    # places where appplication source goes
    app_paths = [
        'galaxy_ng/'
    ]

    # places where test code goes
    test_paths = [
        'galaxy_ng/tests',
        'dev/oci_env_integration',
    ]

    def is_app_path(fn):
        return any(fn.startswith(ap) for ap in app_paths)

    def is_test_path(fn):
        return any(fn.startswith(tp) for tp in test_paths)

    # exit early if no non-test changed in the api code
    app_changed = False
    for cf in changed_files:
        if is_app_path(cf) and not is_test_path(cf):
            app_changed = True
    if not app_changed:
        return

    # look for any changes to file in the tests dirs
    tests_found = False
    for cf in changed_files:
        for tp in test_paths:
            if cf.startswith(tp):
                tests_found = True
                break
        if tests_found:
            break

    if not tests_found:
        raise Exception('Tests should be added or modified with -every- PR!!!')


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # these users should not be checked
    skip_users = ['dependabot[bot]', 'patchback[bot]']

    # the pr submitter
    pr_user = os.environ.get("GITHUB_USER")
    print(f'PR-USER: {pr_user}')

    if pr_user in skip_users:
        print(f'{pr_user} is not required to add tests')
        sys.exit(0)

    # merge branch ...
    pr_branch = get_current_branch()
    if not pr_branch:
        pr_branch = json.loads(os.environ.get('GITHUB_CONTEXT'))['ref']
    print(f'PR-BRANCH: {pr_branch}')

    # branch the PR wants to change
    target_branch = os.environ.get("GITHUB_BASE_REF", "master")
    print(f'TARGET-BRANCH: {target_branch}')
    if target_branch != 'master':
        print('TDD is only enforced on the master branch')
        sys.exit(0)

    changed_files = get_changed_files(pr_branch, target_branch=target_branch)
    for cf in changed_files:
        print(f'modified file: {cf}')
    verify_test_files_changed(changed_files)


if __name__ == "__main__":
    main()
