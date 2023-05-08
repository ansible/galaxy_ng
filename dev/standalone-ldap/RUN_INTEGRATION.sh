#!/bin/bash

# Expected to be called by:
# - GitHub Actions ci_standalone.yml for DeploymentMode.STANDALONE
# - Developer Env makefile commands for DeploymentMode.STANDALONE
# - TODO: Ephemeral Env pr_check.sh (merge smoke_test.sh into this) for DeploymentMode.INSIGHTS

set -e

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

echo "Setting up test data"
CONTAINER=$(docker ps --filter="name=galaxy_ng" --format="table {{.Names}}" | grep -F api)
docker exec -i "$CONTAINER" /entrypoint.sh manage shell < dev/common/setup_test_data.py


#export HUB_API_ROOT='http://localhost:5001/api/'
pytest --capture=no --tb=short -m "standalone_only and ldap" "$@" -v galaxy_ng/tests/integration
RC=$?

exit $RC
