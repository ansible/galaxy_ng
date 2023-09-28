#!/bin/bash

set -e

export HUB_UPLOAD_SIGNATURES=true
export IQE_VAULT_ROLE_ID=${IQE_VAULT_ROLE_ID}
export IQE_VAULT_SECRET_ID=${IQE_VAULT_SECRET_ID}
export HUB_USE_MOVE_ENDPOINT=true
export HUB_API_ROOT="https://galaxy-stage.ansible.com/api/"

which virtualenv || pip3 install virtualenv

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip

if [[ ! -d $VENVPATH ]]; then
    virtualenv $VENVPATH
    $PIP install --retries=0 --verbose --upgrade pip wheel
fi
source $VENVPATH/bin/activate
echo "PYTHON: $(which python)"

pip3 install --upgrade pip wheel

pip3 install -r integration_requirements.txt

pytest --log-cli-level=DEBUG -m "galaxy_stage_ansible" --junitxml=galaxy_ng-results.xml -v galaxy_ng/tests/integration
