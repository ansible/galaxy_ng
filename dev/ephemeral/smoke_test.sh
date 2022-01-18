#!/bin/bash

echo "SMOKE TEST!"

# Need to fix the user first ...
oc project ${NAMESPACE}
AH_API_POD=$(oc get pod -l pod=automation-hub-galaxy-api -o custom-columns=POD:.metadata.name --no-headers | head -1)
oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/ephemeral/fixuser.py

# What is the username?
export HUB_USERNAME="jdoe"

# What is the password?
export HUB_PASSWORD="redhat"

# What is the token?
export HUB_TOKEN="abcdefghijklmnopqrstuvwxyz1234567890"

# What is the api root?
export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com"
echo "HUB_API_ROOT: ${HUB_API_ROOT}"


for X in $(seq 1500 -1 0); do
    echo "SLEEP ${X}"
    sleep 1
done
