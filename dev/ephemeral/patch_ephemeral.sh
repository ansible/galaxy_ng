#!/bin/bash

# Set the CONTENT_ORIGIN URL
FE_ROUTE=$(oc get routes | awk '{print $1}' | grep front-end-aggregator)
if [ -n "${FE_ROUTE}" ]; then
  CONTENT_ORIGIN=$(oc get route front-end-aggregator -o jsonpath='https://{.spec.host}{"\n"}')
else
  CONTENT_ORIGIN=$(bonfire namespace describe ${NAMESPACE} | grep "Gateway route" | awk '{print $3}')
fi
if [ -z "${CONTENT_ORIGIN}" ]; then
  echo "ERROR: unable to determine CONTENT_ORIGIN"
  exit 1
else
  echo "CONTENT_ORIGIN = ${CONTENT_ORIGIN}"
fi
oc patch clowdapp automation-hub --type=json \
    -p '[{"op": "replace",
            "path": "/spec/deployments/1/podSpec/env/1/value",
            "value": "'"${CONTENT_ORIGIN}"'"
        }]'
sleep 5
oc rollout status deploy/automation-hub-galaxy-api

# Fix the routing for minio and artifact urls
oc create route edge minio --service=env-${NAMESPACE}-minio --insecure-policy=Redirect
MINIO_ROUTE=$(oc get route minio -o jsonpath='https://{.spec.host}{"\n"}')
oc patch clowdapp automation-hub \
    --type=json \
    -p '[{"op": "add", "path": "/spec/deployments/2/podSpec/env/-", "value": {
                "name": "PULP_AWS_S3_ENDPOINT_URL",
                "value": "'"${MINIO_ROUTE}"'"
            }
        }]'
sleep 5
oc rollout status deploy/automation-hub-pulp-content-app


echo "Setting up test data"
AH_API_POD=$(oc get pod -l pod=automation-hub-galaxy-api -o jsonpath='{.items[0].metadata.name}')
oc exec $AH_API_POD -c automation-hub-galaxy-api -i -- /entrypoint.sh manage shell < dev/common/setup_test_data.py
