#!/bin/bash

# Expected to be called by:
# - GitHub Actions ci_standalone.yml for DeploymentMode.STANDALONE
# - Developer Env makefile commands for DeploymentMode.STANDALONE
# - TODO: Ephemeral Env pr_check.sh (merge smoke_test.sh into this) for DeploymentMode.INSIGHTS

set -e

export HUB_USE_MOVE_ENDPOINT="true"
export HUB_API_ROOT="http://localhost:5001/api/automation-hub"

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
docker exec -i galaxy_ng_api_1 /entrypoint.sh manage shell < dev/common/setup_test_data.py

# when running user can specify extra pytest arguments such as
# export HUB_LOCAL=1
# dev/common/RUN_INTEGRATION.sh --pdb -sv --log-cli-level=DEBUG "-m standalone_only" -k mytest
if [[ -z $HUB_LOCAL ]]; then
    pytest --capture=no -m "not standalone_only" $@ -v galaxy_ng/tests/integration
    RC=$?
else
    pytest --capture=no -m "not cloud_only" -v $@ galaxy_ng/tests/integration
    RC=$?

    if [[ $RC != 0 ]]; then
        # dump the api logs
        docker logs galaxy_ng_api_1

        # dump the worker logs
        docker logs galaxy_ng_worker_1
    fi

fi

exit $RC
