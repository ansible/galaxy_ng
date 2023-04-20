#!/bin/bash

# Expected to be called by:
# - GitHub Actions ci_standalone.yml for DeploymentMode.STANDALONE
# - Developer Env makefile commands for DeploymentMode.STANDALONE
# - TODO: Ephemeral Env pr_check.sh (merge smoke_test.sh into this) for DeploymentMode.INSIGHTS

set -e

export HUB_API_ROOT="http://localhost:8080/api/automation-hub/"
export HUB_AUTH_URL="http://localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token"
export HUB_USE_MOVE_ENDPOINT="true"
unset HUB_TOKEN

which virtualenv || pip install --user virtualenv

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip

if [[ ! -d $VENVPATH ]]; then
    virtualenv $VENVPATH
    $PIP install --retries=0 --verbose --upgrade pip wheel
fi
source $VENVPATH/bin/activate
echo "PYTHON: $(which python)"

pip install -r integration_requirements.txt
pip show epdb || pip install epdb

# when running user can specify extra pytest arguments such as
# export HUB_LOCAL=1
# dev/common/RUN_INTEGRATION.sh --pdb -sv --log-cli-level=DEBUG "-m standalone_only" -k mytest

pytest --capture=no --tb=short -m "not standalone_only and not community_only and not rbac_roles and not iqe_rbac_test and not sync and not rm_sync and not x_repo_search and not rbac_repos" $@ -v galaxy_ng/tests/integration
RC=$?

exit $RC
