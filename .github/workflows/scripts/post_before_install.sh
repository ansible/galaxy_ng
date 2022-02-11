#!/usr/bin/env bash

# This script runs after the before_install script.
# Features on this script:
# 
# - If worflow is Nightly Latest then it forces RUN_ON_LATESTS to 1.
# - Else, if event is not 'pull_request' then it skips the script.
# - Read the last commit message and extracts environment variables from it.
#   - Commit message format: 'env:KEY=value' is parsed and the environment variables are set.
#   - Available envvars: 
#     RUN_ON_LATEST - If set to 1, the script will checkout to main/master branches for all repos.
#     LOCK_REQUIREMENTS - If set to 0, the script will unpin requirements from galaxy_ng/setup.py.
#     <REPO>_REVISION - If set to specific git commit sha, the script will checkout to that commit.
#        The above can be commit, tag, branch, or any other git ref. e.g:
#        env: PULPCORE_REVISION=36692a8c628a5d5af220fb1c7bede712727e1e89
#        env: GALAXY_IMPORTER_REVISION=branch_foo
#

echo "Workflow name: $GITHUB_WORKFLOW"
if [ "$GITHUB_WORKFLOW" == "Nightly Latest" ]; then
    echo "Forcing RUN_ON_LATEST=1"
    RUN_ON_LATEST=1
    export RUN_ON_LATEST
    LOCK_REQUIREMENTS=1
    export LOCK_REQUIREMENTS
else
    if [ "$GITHUB_EVENT_NAME" != "pull_request" ]; then
        echo "Skipping post_before_install.sh because this is not a pull request or nightly latest job."
        exit 0
    fi

    # Read the latest commit message
    COMMIT_MSG=$(git log --format=%B --no-merges -1)
    export COMMIT_MSG

    # Read the commit message and extract the environment variables from there
    # lines containing the format: 'env:NAME=value' are parsed
    set -o allexport
    eval $(echo "${COMMIT_MSG}" | grep 'env:' | awk -F '["=]+' '{print substr($1, 5)"="$2}')
    set +o allexport
    # Alternative implementation to above logic.
    # export $(echo "${COMMIT_MSG}" | grep 'env:' | awk -F '["=]+' '{print substr($1, 5)"="$2}' | xargs)
fi

# Unpin Requirements from galaxy_ng setup.py?
# This runs when commit has 'env:LOCK_REQUIRENTS=0'
# Also forced when 'env:RUN_ON_LATEST=1'
if [[ "${LOCK_REQUIREMENTS:-1}" == "0" ]] || [[ "${RUN_ON_LATEST:-0}" == "1" ]] ; then
    echo "Unpinning requirements"
    original='unpin_requirements = os.getenv("LOCK_REQUIREMENTS") == "0"'
    new='unpin_requirements = True'
    sed -i "s/$original/$new/g" setup.py
    grep 'unpin_requirements' setup.py
fi

# Got to parent directory where repos are cloned
cd ..

function get_main_branch_of_repo {
    local repo=$1
    local branch

    # tried the following but it didn't work, it was always returning checked out branch.
    # branch=$(git -C "$repo" rev-parse --abbrev-ref HEAD)
    # but this works
    branch=$(git -C "$repo" remote show origin | awk '/HEAD branch/ {print $NF}')

    if [[ "$branch" == "HEAD" ]]; then
        branch=$(git -C "$repo" symbolic-ref --short HEAD)
    fi

    echo "$branch"
}

# if env:RUN_ON_LATEST=1, then checkout all the repos to main branches
if [[ "${RUN_ON_LATEST:-0}" == "1" ]]; then
    echo "Running on latest main branches for repos."
    export GALAXY_IMPORTER_REVISION=$(get_main_branch_of_repo galaxy-importer)
    export PULPCORE_REVISION=$(get_main_branch_of_repo pulpcore)
    export PULP_ANSIBLE_REVISION=$(get_main_branch_of_repo pulp_ansible)
    export PULP_CONTAINER_REVISION=$(get_main_branch_of_repo pulp_container)
fi

# if env:<REPO>_REVISION is set, then checkout that revision
for repo in galaxy-importer pulp_container pulp_ansible pulpcore; do
    UPPER_REPO=$(echo "${repo}" | tr '[:lower:]' '[:upper:]' | tr '-' '_')
    export VARNAME="${UPPER_REPO}_REVISION"
    if [[ "${!VARNAME+x}" ]]; then
        revision="${!VARNAME}"
        echo "Checking out ${repo} to ${revision}"
        # read the repo origin url
        repourl=$(git -C $repo config --get remote.origin.url)
        # delete the current repo directory and start a new git repo
        rm -rf "${repo}"
        mkdir "${repo}"
        git -C $repo init
        # add the remote repo url and fetch the specific revision
        git -C $repo remote add origin "${repourl}"
        git -C $repo fetch origin "${revision}"
        git -C $repo reset --hard FETCH_HEAD
    fi
done

# back to the directory where the workflow is being run
cd galaxy_ng || exit
