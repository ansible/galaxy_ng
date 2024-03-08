#!/bin/bash

set -x
set -e

echo "Creating virtualenv for testing ..."
VENV_PATH=/tmp/gvenv
python3 -m venv ${VENV_PATH}
source ${VENV_PATH}/bin/activate
${VENV_PATH}/bin/pip install --upgrade pip wheel
${VENV_PATH}/bin/pip install -r integration_requirements.txt

echo "Running pytest ..."
${VENV_PATH}/bin/pytest \
    --capture=no --log-cli-level=ERROR -m "deployment_cloud or all" \
    -v \
    galaxy_ng/tests/integration $@
RC=$?
exit $RC
