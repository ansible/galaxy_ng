#!/bin/bash

echo "SMOKE TEST!"

echo "Set project to ${NAMESPACE}"
oc project ${NAMESPACE}

echo "Find galaxy-api pod"
AH_API_POD=$(oc get pod -l pod=automation-hub-galaxy-api -o custom-columns=POD:.metadata.name --no-headers | head -1)

echo "Fixing keycloak user permissions"
oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/ephemeral/fixuser.py

echo "Create token for keycloak user"
oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/ephemeral/create_token.py


# What is the username?
export HUB_USERNAME="jdoe"

# What is the password?
export HUB_PASSWORD="redhat"

# What is the token?
export HUB_TOKEN="abcdefghijklmnopqrstuvwxyz1234567890"

# What is the api root?
export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/api/automation-hub/"
echo "HUB_API_ROOT: ${HUB_API_ROOT}"

echo "Creating virtualenv for testing ..."
VENV_PATH=gvenv
virtualenv ${VENV_PATH}
source ${VENV_PATH}/bin/activate
${VENV_PATH}/bin/pip install --upgrade pip wheel
${VENV_PATH}/bin/pip install -r galaxy_ng/tests/integration/requirements.txt

echo "Running pytest ..."
${VENV_PATH}/bin/pytest --capture=no -m "not standalone_only" -v galaxy_ng/tests/integration

echo "Starting sleep cycle ..."
for X in $(seq 1500 -1 0); do
    echo "SLEEP ${X}"
    sleep 1
done
