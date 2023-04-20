#!/bin/bash

set -e

export HTTPS_PROXY="http://squid.corp.redhat.com:3128"
export HUB_UPLOAD_SIGNATURES=true
export IQE_VAULT_GITHUB_TOKEN=${IQE_VAULT_GITHUB_TOKEN}
export IQE_VAULT_ROLE_ID=${IQE_VAULT_ROLE_ID}
export IQE_VAULT_SECRET_ID=${IQE_VAULT_SECRET_ID}
export TESTS_AGAINST_STAGE=true
export HUB_USE_MOVE_ENDPOINT=true
export HUB_API_ROOT="https://console.stage.redhat.com/api/automation-hub/"
export HUB_AUTH_URL="https://sso.stage.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token/"

which virtualenv || pip3 install virtualenv

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip

if [[ ! -d $VENVPATH ]]; then
    virtualenv $VENVPATH
    $PIP install --retries=0 --verbose --upgrade pip wheel
fi
source $VENVPATH/bin/activate
echo "PYTHON: $(which python)"

pip3 install --upgrade pip wheel

pip3 install -r integration_requirements.txt

pytest --log-cli-level=DEBUG -m "not standalone_only and not community_only and not rbac_roles and not slow_in_cloud and not iqe_rbac_test and not sync and not rm_sync and not x_repo_search and not rbac_repos" --junitxml=galaxy_ng-results.xml -v galaxy_ng/tests/integration
