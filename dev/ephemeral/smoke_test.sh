#!/bin/bash

set -x
set -e

echo "SMOKE TEST!"

# always force docker for integration tests
GALAXY_USE_DOCKER=${GALAXY_USE_DOCKER:=1}

echo "System info ..."
cat /etc/redhat-release
cat /etc/issue

echo "RPM packages ..."
rpm -qa | sort

echo "Set project to ${NAMESPACE}"
oc project ${NAMESPACE}

echo "Find galaxy-api pod"
AH_API_POD=$(oc get pod -l pod=automation-hub-galaxy-api -o custom-columns=POD:.metadata.name --no-headers | head -1)

echo "Setting up test data"
oc exec -i $AH_API_POD /entrypoint.sh manage shell < dev/common/setup_test_data.py

# Force "publishing" uploaded collections
export HUB_USE_MOVE_ENDPOINT="true"

# What is the api root?
export HUB_API_ROOT="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/api/automation-hub/"
echo "HUB_API_ROOT: ${HUB_API_ROOT}"
export HUB_AUTH_URL="https://mocks-keycloak-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com/auth/realms/redhat-external/protocol/openid-connect/token"
echo "HUB_AUTH_URL: ${HUB_AUTH_URL}"


if [[ $GALAXY_USE_DOCKER == 0 ]]; then
    echo "--------------------------------------------------"
    echo "  Running tests directly from $(hostname -f)"
    echo "--------------------------------------------------"
    bash dev/ephemeral/run_tests.sh $@
    RC=$?
    exit $RC

else
    # devshift is el7, so python is quite old and incompatible with core ...
    echo "--------------------------------------------------"
    echo "  Launching docker container for tests"
    echo "--------------------------------------------------"

    # default to docker, use podman if not found
    DOCKERCMD="docker"
    if ! command -v docker &>/dev/null && command -v podman &> /dev/null; then
        DOCKERCMD="podman"
    fi

    #DOCKER_IMAGE="python:3"
    DOCKER_IMAGE="quay.io/fedora/python-310"
    $DOCKERCMD run \
        -v $(pwd):/app \
        --env HUB_USE_MOVE_ENDPOINT="${HUB_USE_MOVE_ENDPOINT}" \
        --env HUB_API_ROOT="${HUB_API_ROOT}" \
        --env HUB_AUTH_URL="${HUB_AUTH_URL}" \
        --rm \
        ${DOCKER_IMAGE} \
        /bin/bash -c "cd /app; bash dev/ephemeral/run_tests.sh"
    RC=$?
    exit $RC
fi
