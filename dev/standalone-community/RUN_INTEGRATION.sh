#!/bin/bash

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
docker exec -i galaxy_ng_api_1 /entrypoint.sh manage shell < dev/common/setup_test_data.py

# social logins will happen against the github mock
export SOCIAL_AUTH_GITHUB_BASE_URL='http://localhost:8082'
export SOCIAL_AUTH_GITHUB_API_URL='http://localhost:8082'

export HUB_API_ROOT='http://localhost:5001/api/'
pytest --capture=no -m "community_only" $@ -v galaxy_ng/tests/integration
RC=$?

exit $RC
