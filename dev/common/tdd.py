#!/usr/bin/env python3

import json
import logging
import os
import subprocess
import sys

from pprint import pprint


def get_current_branch():
    pid = subprocess.run('git branch --show-current', shell=True, stdout=subprocess.PIPE, check=True)
    branch_name = pid.stdout.decode('utf-8')
    branch_name = branch_name.strip()
    return branch_name


def get_changed_files(pr_branch, target_branch="master"):
    cmd = f'git diff --name-only {pr_branch}..{target_branch}'
    pid = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, check=True)
    filenames = pid.stdout.decode('utf-8')
    filenames = filenames.split('\n')
    filenames = [x.strip() for x in filenames if x.strip()]
    return filenames


def verify_test_files_changed(changed_files):
    expected_paths = [
        'galaxy_ng/tests'
    ]
    found = False
    for cf in changed_files:
        for ep in expected_paths:
            if cf.startswith(ep):
                found = True
                break
        if found:
            break

    if not found:
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
