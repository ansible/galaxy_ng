#!/bin/bash

if [[ -z $HUB_LOCAL ]]; then
    export NAMESPACE="ephemeral-1riioj"
    export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/api/automation-hub/"
    export HUB_AUTH_URL="https://keycloak-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/auth/realms/redhat-external/protocol/openid-connect/token"
    export HUB_USERNAME="jdoe"
    export HUB_PASSWORD="redhat"
    export HUB_USE_MOVE_ENDPOINT="true"
    unset HUB_TOKEN
else
    unset NAMESPACE
    unset HUB_API_ROOT
    unset HUB_AUTH_URL
    unset HUB_USERNAME
    unset HUB_PASSWORD
    export HUB_USE_MOVE_ENDPOINT="true"
    export HUB_TOKEN="abcdefghijklmnopqrstuvwxyz1234567890"
fi


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
if [[ -z $HUB_LOCAL ]]; then
    pytest --capture=no -m "not standalone_only" $@ -v galaxy_ng/tests/integration
    #pytest --capture=no --pdb -v $@ galaxy_ng/tests/integration
else
    pytest --capture=no -m "not cloud_only" -v $@ galaxy_ng/tests/integration
fi
