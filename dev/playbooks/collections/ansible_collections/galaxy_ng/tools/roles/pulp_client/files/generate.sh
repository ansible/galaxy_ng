#!/bin/bash -x

set -e

PULP_IP=$1
PLUGIN=$2

cd ../../..
if [[ ! -d pulp-openapi-generator ]]; then
    git clone https://github.com/pulp/pulp-openapi-generator
fi
cd pulp-openapi-generator;

export USE_LOCAL_API_JSON=true;
export PULP_URL="https://${PULP_IP}/api/galaxy/pulp/api/v3/";

curl -L -k -u admin:password -o status.json "https://${PULP_IP}/api/galaxy/pulp/api/v3/status/";
curl -L -k -u admin:password -o api.json "https://${PULP_IP}/api/galaxy/pulp/api/v3/docs/api.json?bindings&plugin=${PLUGIN}";

if [ "${PLUGIN}" == "galaxy_ng" ]; then
    cat status.json | head
    export REPORTED_VERSION=$(jq '.versions[] | select (.component == "galaxy").version' status.json | tr -d '"')
    echo "REPORTED_VERSION: ${REPORTED_VERSION}"
    export VERSION="$(echo "$REPORTED_VERSION" | python -c 'from packaging.version import Version; print(Version(input()))')"
    echo "FINAL_VERSION: ${FINAL_VERSION}"
else
    export VERSION=""
fi;

bash -x generate.sh ${PLUGIN} python ${VERSION}
