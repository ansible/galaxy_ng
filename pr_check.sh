#!/bin/bash

# --------------------------------------------
# Check if changed files begin with one of the ignored prefixes
# and if all do then skip running remainder of script
# Example ignored prefixes: "docs/", "CHANGES/"
# --------------------------------------------
FILES_CHANGED=$(git diff origin/main --name-only)
echo FILES_CHANGED=$FILES_CHANGED
skip_pr_check="true"
for line in $FILES_CHANGED; do
    if ! [[ $line =~ ^("docs/"|"CHANGES/"|"mkdocs.yml"|".github/") ]]; then skip_pr_check="false"; fi
done

# Need to make a dummy results file to make tests pass
mkdir -p artifacts
cat << EOF > artifacts/junit-dummy.xml
<testsuite tests="1">
    <testcase classname="dummy" name="dummytest"/>
</testsuite>
EOF

if [ $skip_pr_check == "true" ]; then exit 0; fi


# --------------------------------------------
# Options that must be configured by app owner
# --------------------------------------------
APP_NAME="automation-hub"  # name of app-sre "application" folder this component lives in
COMPONENT_NAME="automation-hub"  # name of app-sre "resourceTemplate" in deploy.yaml for this component
IMAGE="quay.io/cloudservices/automation-hub-galaxy-ng"
COMPONENTS_W_RESOURCES="all"  # components which should preserve resource settings (optional, default: none)

export IMAGE_FRONTEND="quay.io/cloudservices/ansible-hub-ui"
export IMAGE_FRONTEND_SHA1=$(curl -s https://api.github.com/repos/ansible/ansible-hub-ui/commits/master | jq -r '.sha')
export IMAGE_FRONTEND_TAG=$(echo ${IMAGE_FRONTEND_SHA1} | head -c7)

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
bonfire deploy \
    ${APP_NAME} \
    --source=appsre \
    --ref-env insights-stage \
    --set-template-ref ${COMPONENT_NAME}=${GIT_COMMIT} \
    --set-image-tag ${IMAGE}=${IMAGE_TAG} \
    --set-template-ref automation-hub-frontend=${IMAGE_FRONTEND_SHA1} \
    --set-image-tag ${IMAGE_FRONTEND}=${IMAGE_FRONTEND_TAG} \
    --frontends=true \
    --namespace ${NAMESPACE} \
    --timeout ${DEPLOY_TIMEOUT} \
    ${COMPONENTS_ARG} \
    ${COMPONENTS_RESOURCES_ARG} \
    --set-parameter ${COMPONENT_NAME}/IMPORTER_JOB_NAMESPACE=${NAMESPACE} \
    --set-parameter ${COMPONENT_NAME}/ENABLE_SIGNING="0" \
    --set-parameter ${COMPONENT_NAME}/GALAXY_SIGNATURE_UPLOAD_ENABLED="false" \
    --set-parameter ${COMPONENT_NAME}/GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL="false" \
    --set-parameter ${COMPONENT_NAME}/GALAXY_AUTO_SIGN_COLLECTIONS="false" \
    --set-parameter ${COMPONENT_NAME}/GALAXY_COLLECTION_SIGNING_SERVICE="''"
# END WORKAROUND
bonfire namespace describe ${NAMESPACE}
oc project ${NAMESPACE}

dev/ephemeral/patch_ephemeral.sh
dev/ephemeral/create_keycloak_users.sh

# source $CICD_ROOT/smoke_test.sh
# source smoke_test.sh
bash dev/ephemeral/smoke_test.sh
RC=$?

# Need to make a dummy results file to make tests pass
mkdir -p artifacts
cat << EOF > artifacts/junit-dummy.xml
<testsuite tests="1">
    <testcase classname="dummy" name="dummytest"/>
</testsuite>
EOF

exit $RC
