#!/bin/bash

set -e

unset NAMESPACE
unset HUB_AUTH_URL
export HUB_USE_MOVE_ENDPOINT="true"


VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip

if [[ ! -d $VENVPATH ]]; then
    python3.10 -m venv $VENVPATH
fi
source $VENVPATH/bin/activate
echo "PYTHON: $(which python)"

$VENVPATH/bin/pip install -r integration_requirements.txt
$VENVPATH/bin/pip show epdb || pip install epdb

CONTAINER_API=$(docker ps --filter="name=galaxy_ng" --format="table {{.Names}}" | grep -F api)
CONTAINER_WORKER=$(docker ps --filter="name=galaxy_ng" --format="table {{.Names}}" | grep -F worker)
echo "Setting up test data"
docker exec -i "$CONTAINER_API" /entrypoint.sh manage shell < dev/common/setup_test_data.py

$VENVPATH/bin/pytest --capture=no -m "rbac_repos" -v $@ galaxy_ng/tests/integration
RC=$?

if [[ $RC != 0 ]]; then
    # dump the api logs
    docker logs "$CONTAINER_API"

    # dump the worker logs
    docker logs "$CONTAINER_WORKER"
fi

exit $RC
