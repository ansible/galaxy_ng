#!/bin/bash

# Expected to be called by:
# - GitHub Actions ci_standalone.yml for DeploymentMode.STANDALONE
# - Developer Env makefile commands for DeploymentMode.STANDALONE
# - TODO: Ephemeral Env pr_check.sh (merge smoke_test.sh into this) for DeploymentMode.INSIGHTS

set -ex

if [[ -z $HUB_LOCAL ]]; then
    export NAMESPACE="ephemeral-1riioj"
    export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/api/automation-hub/"
    export HUB_AUTH_URL="https://mocks-keycloak-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/auth/realms/redhat-external/protocol/openid-connect/token"
    export HUB_USE_MOVE_ENDPOINT="true"
    unset HUB_TOKEN
else
    unset NAMESPACE
    unset HUB_AUTH_URL
    export HUB_USE_MOVE_ENDPOINT="true"
fi

# which virtualenv || pip install --user virtualenv

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip

if [[ ! -d $VENVPATH ]]; then
    #virtualenv $VENVPATH
    python3.10 -m venv $VENVPATH
    # $PIP install --retries=0 --verbose --upgrade pip wheel
fi
source $VENVPATH/bin/activate
echo "PYTHON: $(which python)"

$VENVPATH/bin/pip install -r integration_requirements.txt
$VENVPATH/bin/pip show epdb || pip install epdb

# when running user can specify extra pytest arguments such as
# export HUB_LOCAL=1
# dev/common/RUN_INTEGRATION.sh --pdb -sv --log-cli-level=DEBUG "-m standalone_only" -k mytest
if [[ -z $HUB_LOCAL ]]; then
    $VENVPATH/bin/pytest --capture=no -m "not standalone_only and not community_only and not rbac_roles and not iqe_rbac_test and not sync" $@ -v galaxy_ng/tests/integration
    RC=$?
else
    $VENVPATH/bin/pytest --capture=no -m "not cloud_only and not community_only and not rbac_roles and not iqe_rbac_test and not sync" -v $@ galaxy_ng/tests/integration
    RC=$?

    if [[ $RC != 0 ]]; then
        # dump the api logs
        docker logs galaxy_ng_api_1

        # dump the worker logs
        docker logs galaxy_ng_worker_1
    fi

fi

exit $RC
