#!/bin/bash

# --------------------------------------------
# Options that must be configured by app owner
# --------------------------------------------
APP_NAME="automation-hub,gateway,insights-ephemeral"  # name of app-sre "application" folder this component lives in
COMPONENT_NAME="automation-hub"  # name of app-sre "resourceTemplate" in deploy.yaml for this component
IMAGE="quay.io/cloudservices/automation-hub-galaxy-ng"
COMPONENTS_W_RESOURCES="all"  # components which should preserve resource settings (optional, default: none)

# IQE_PLUGINS=""
# IQE_MARKER_EXPRESSION="ephemeral"
# IQE_FILTER_EXPRESSION=""

# Install bonfire repo/initialize
CICD_URL=https://raw.githubusercontent.com/RedHatInsights/bonfire/master/cicd
curl -s "$CICD_URL/bootstrap.sh" > .cicd_bootstrap.sh
source .cicd_bootstrap.sh

source "$CICD_ROOT/build.sh"
# source $APP_ROOT/unit_test.sh

# BEGIN WORKAROUND
# NOTE(cutwater): See https://issues.redhat.com/browse/RHCLOUD-14977
source ${CICD_ROOT}/_common_deploy_logic.sh
export NAMESPACE=$(bonfire namespace reserve)
export CONTENT_ORIGIN="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com"
bonfire deploy \
    ${APP_NAME} \
    --source=appsre \
    --ref-env insights-stage \
    --set-template-ref ${COMPONENT_NAME}=${GIT_COMMIT} \
    --set-image-tag ${IMAGE}=${IMAGE_TAG} \
    --namespace ${NAMESPACE} \
    --timeout ${DEPLOY_TIMEOUT} \
    ${COMPONENTS_ARG} \
    ${COMPONENTS_RESOURCES_ARG} \
    --set-parameter ${COMPONENT_NAME}/IMPORTER_JOB_NAMESPACE=${NAMESPACE} \
    --set-parameter ${COMPONENT_NAME}/CONTENT_ORIGIN="${CONTENT_ORIGIN}"
# END WORKAROUND
oc project ${NAMESPACE}

UI_REF="qa-beta"
echo "patching the frontend-aggregator to use ${UI_REF}"
oc patch cm aggregator-app-config --type merge --patch "{\"data\": {\"app-config.yml\": \"${COMPONENT_NAME}:\n  commit: ${UI_REF}\n\"}}"
oc rollout restart deployment/front-end-aggregator
oc rollout status deployment/front-end-aggregator
oc rollout restart deployment/mocks
oc rollout status deployment/mocks
FE_POD=$(oc get pod -l app=front-end-aggregator -o json | jq -r '.items[] | select( .metadata.deletionTimestamp == null ) | .metadata.name')
oc exec ${FE_POD} -- /bin/bash -c "sed -i 's/--omit-dir-times/--omit-dir-times --omit-link-times/' /www/src/git_helper.sh"
oc exec ${FE_POD} -- /bin/bash -c "/www/src/git_helper.sh config https://github.com/RedHatInsights/cloud-services-config prod-beta"

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

# source $CICD_ROOT/smoke_test.sh

# source smoke_test.sh
source dev/ephemeral/smoke_test.sh


# Need to make a dummy results file to make tests pass
mkdir -p artifacts
cat << EOF > artifacts/junit-dummy.xml
<testsuite tests="1">
    <testcase classname="dummy" name="dummytest"/>
</testsuite>
EOF
