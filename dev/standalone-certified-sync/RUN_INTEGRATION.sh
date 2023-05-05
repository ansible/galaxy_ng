#!/bin/bash

set -e

unset NAMESPACE
unset HUB_AUTH_URL
export HUB_USE_MOVE_ENDPOINT="true"

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
$VENVPATH/bin/pytest --capture=no -m "certified_sync or rm_sync" -v "$@" galaxy_ng/tests/integration
RC=$?

if [[ $RC != 0 ]]; then
    CONTAINER_API=$(docker ps --filter="name=galaxy_ng" --format="table {{.Names}}" | grep -F api)
    CONTAINER_WORKER=$(docker ps --filter="name=galaxy_ng" --format="table {{.Names}}" | grep -F worker)
    # dump the api logs
    docker logs "$CONTAINER_API"

    # dump the worker logs
    docker logs "$CONTAINER_WORKER"
fi

exit $RC
