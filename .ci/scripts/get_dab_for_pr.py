#!/usr/bin/env python3
"""
CI script to handle Django Ansible Base (DAB) dependency management for PRs.

This script performs two main functions:
1. Checks out a specific DAB branch/PR when referenced in galaxy_ng PRs
2. Updates requirements.insights.txt to use the checked out DAB version

The script has two checkout strategies:
- Primary: Scan PR body for "requires" links to specific DAB PRs
- Secondary (fallback): Look for matching branch names in the DAB repository
"""

import os
import re
import sys

import requests

# --- Configuration ---
DAB_REPO = "ansible/django-ansible-base"
GITHUB_API_URL = "https://api.github.com"
# ---

# --- Get CI Environment Variables ---
pr_body = os.environ.get("PR_BODY", "")
# For pull requests, GITHUB_BASE_REF is the base branch (only set on PRs).
# For push events, GITHUB_REF_NAME is the branch name.
current_branch = os.environ.get("GITHUB_BASE_REF") or os.environ.get("GITHUB_REF_NAME")

# --- GitHub Authentication ---
headers = {}
gh_token = os.environ.get("GH_TOKEN")
if gh_token:
    headers["Authorization"] = f"Bearer {gh_token}"

# --- Primary Check: Scan PR Body for 'requires' link ---
print("🚀 Starting build process...")
print("Performing primary check: Scanning PR body for a 'requires' link...")
print(f'Scanning body: "{pr_body[:100]}..."')

requires_re = re.compile(f"requires.*{DAB_REPO}(?:#|/pull/)([0-9]+)", re.IGNORECASE)
matches = requires_re.search(pr_body)

# Initialize variables to track checkout status and branch info
dab_checked_out = False
branch = None
repo_url = None

if matches:
    required_pr = matches.group(1)
    print(f"✅ Found requirement for DAB PR #{required_pr}.")

    pr_url = f"{GITHUB_API_URL}/repos/{DAB_REPO}/pulls/{required_pr}"
    response = requests.get(pr_url, headers=headers)

    if response.status_code == 200:
        pr_data = response.json()
        branch = pr_data["head"]["ref"]
        repo_url = pr_data["head"]["repo"]["html_url"]

        if not pr_data.get("merged"):
            print(f"Checking out branch '{branch}' from '{repo_url}'...")
            exit_code = os.system(
                f"cd .. && git clone {repo_url} -b {branch} --depth=1 django-ansible-base"
            )
            if exit_code == 0:
                dab_checked_out = True
                print(f"✅ Successfully checked out DAB branch '{branch}'")
            else:
                print(f"❌ Failed to checkout DAB branch '{branch}'")
                sys.exit(1)
        else:
            print(
                f"✅ The referenced PR #{required_pr} has already been merged. No checkout needed."
            )
    else:
        print(
            f"❌ Error: Could not fetch data for PR #{required_pr}. Status: {response.status_code}"
        )
        # Continue to secondary check as a fallback
else:
    print("No 'requires' link found in PR body.")

# --- Secondary Check (Fallback): Look for a matching branch ---
if not dab_checked_out:
    print("\nPerforming secondary check: Looking for a matching branch...")

    if current_branch:
        print(f"Current branch detected as '{current_branch}'.")
        print(f"Checking for a matching branch in '{DAB_REPO}'...")
        branch = current_branch

        branch_url = f"{GITHUB_API_URL}/repos/{DAB_REPO}/branches/{current_branch}"
        response = requests.get(branch_url, headers=headers)

        if response.status_code == 200:
            print(f"✅ Success! Found matching branch '{current_branch}' in '{DAB_REPO}'.")
            repo_url = f"https://github.com/{DAB_REPO}.git"
            print(f"Checking out '{current_branch}' from '{repo_url}'...")
            exit_code = os.system(
                f"cd .. && git clone {repo_url} -b {current_branch} --depth=1 django-ansible-base"
            )
            if exit_code == 0:
                dab_checked_out = True
                print(f"✅ Successfully checked out DAB branch '{current_branch}'")
            else:
                print(f"❌ Failed to checkout DAB branch '{current_branch}'")
                sys.exit(1)
        else:
            print(f"No matching branch found in '{DAB_REPO}'.")
    else:
        print("Could not determine the current branch from CI environment variables.")

# --- Configure environment for Docker compose ---
if dab_checked_out:
    print("\n🔧 Configuring environment for DAB editable install...")

    # Set environment variable to indicate DAB is available for compose
    with open(os.environ.get("GITHUB_ENV", "/dev/null"), "a") as env_file:
        env_file.write("DEV_SOURCE_PATH=django-ansible-base\n")

    # Update requirements file to use the specific DAB branch we checked out
    requirements_file = "requirements/requirements.insights.txt"
    print(f"📝 Updating {requirements_file} to use local django-ansible-base checkout...")

    try:
        # Read the current requirements file
        with open(requirements_file) as f:
            lines = f.readlines()

        # Find and replace the django-ansible-base line
        # Expected format: django-ansible-base[extras] @ git+https://github.com/repo@branch
        modified = False
        for i, line in enumerate(lines):
            if line.strip().startswith("django-ansible-base"):
                # Parse the existing line: django-ansible-base[extras] @ git+url@old_branch
                if " @ git+" in line:
                    package_part, url_part = line.strip().split(" @ git+", 1)
                    # Construct new line with the checked out branch
                    new_line = f"{package_part} @ git+{repo_url.strip('.git')}@{branch}\n"

                    if lines[i] != new_line:
                        lines[i] = new_line
                        modified = True
                        print(f"📝 Updated DAB line from: {line.strip()}")
                        print(f"📝                    to: {new_line.strip()}")
                    break
                else:
                    print(
                        f"⚠️ Warning: Unexpected format in django-ansible-base line: {line.strip()}"
                    )

        if modified:
            # Write the modified requirements file
            with open(requirements_file, "w") as f:
                f.writelines(lines)
            print(f"✅ Updated {requirements_file} for local DAB checkout")
        else:
            print(f"No changes needed in {requirements_file}")

    except FileNotFoundError:
        print(f"⚠️ Warning: {requirements_file} not found")
    except Exception as e:
        print(f"❌ Error updating {requirements_file}: {e}")

    print("✅ Environment configured for DAB checkout")
else:
    print("\nNo DAB checkout performed. Using default django-ansible-base dependency.")
