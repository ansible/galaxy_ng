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

echo "Setting up test data"
docker exec -i galaxy_ng_api_1 /entrypoint.sh manage shell < dev/common/setup_test_data.py

$VENVPATH/bin/pytest --capture=no -m "iqe_rbac_test" -v $@ galaxy_ng/tests/integration
RC=$?

if [[ $RC != 0 ]]; then
    # dump the api logs
    docker logs galaxy_ng_api_1

    # dump the worker logs
    docker logs galaxy_ng_worker_1
fi

exit $RC
