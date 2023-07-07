#!/bin/bash

if [[ -z $DUMP_LOGS ]]; then
    set -e
fi

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

CONTAINER=$(docker ps --filter="name=galaxy_ng" --format="table {{.Names}}" | grep -F api)

echo "Setting up test data"
docker exec -i "$CONTAINER" /entrypoint.sh manage shell < dev/common/setup_test_data.py

# social logins will happen against the github mock
export SOCIAL_AUTH_GITHUB_BASE_URL='http://localhost:8082'
export SOCIAL_AUTH_GITHUB_API_URL='http://localhost:8082'

export HUB_API_ROOT='http://localhost:5001/api/'
pytest --capture=no -m "deployment_community or all" "$@" -v galaxy_ng/tests/integration
RC=$?

if [[ $RC != 0 && -n "$DUMP_LOGS" ]]; then
    echo "DUMPING LOGS!"
    for CNAME in $(docker ps --format '{{ .Names }}'); do
        echo "----------------------------------------"
        echo "$CNAME"
        echo "----------------------------------------"
        docker logs "$CNAME"
    done
fi

exit $RC
