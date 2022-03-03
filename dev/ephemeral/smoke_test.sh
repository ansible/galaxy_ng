#!/bin/bash

echo "SMOKE TEST!"

echo "System info ..."
cat /etc/redhat-release
cat /etc/issue

echo "RPM packges ..."
rpm -qa 

echo "Set project to ${NAMESPACE}"
oc project ${NAMESPACE}

echo "Find galaxy-api pod"
AH_API_POD=$(oc get pod -l pod=automation-hub-galaxy-api -o custom-columns=POD:.metadata.name --no-headers | head -1)

echo "Fixing keycloak user permissions"
oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/ephemeral/fixuser.py

#echo "Create token for keycloak user"
#oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/ephemeral/create_token.py

echo "Creating test data"
oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/ephemeral/create_objects.py

# What is the username?
export HUB_USERNAME="jdoe"

# What is the password?
export HUB_PASSWORD="redhat"

# What is the token?
#export HUB_TOKEN="abcdefghijklmnopqrstuvwxyz1234567890"

# Force "publishing" uploaded collections
export HUB_USE_MOVE_ENDPOINT="true"

# What is the api root?
export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/api/automation-hub/"
echo "HUB_API_ROOT: ${HUB_API_ROOT}"
export HUB_AUTH_URL="https://keycloak-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/auth/realms/redhat-external/protocol/openid-connect/token"
echo "HUB_AUTH_URL: ${HUB_AUTH_URL}"

echo "Creating virtualenv for testing ..."
VENV_PATH=gvenv
virtualenv --python=$(which python3) ${VENV_PATH}
source ${VENV_PATH}/bin/activate
${VENV_PATH}/bin/pip install --upgrade pip wheel
${VENV_PATH}/bin/pip install -r integration_requirements.txt

echo "Running pytest ..."
${VENV_PATH}/bin/pytest --capture=no -m "cloud_only or not standalone_only" -v galaxy_ng/tests/integration

#echo ""
#echo "##################################################"
#echo "# API POD LOGS"
#echo "##################################################"
#echo ""
#oc logs $AH_API_POD

#echo "Starting sleep cycle for 10000s... "
#for X in $(seq 10000 -1 0); do
#    #echo "SLEEP ${X}"
#    sleep 1
#done
