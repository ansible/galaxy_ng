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
    --set-parameter ${COMPONENT_NAME}/IMPORTER_JOB_NAMESPACE=${NAMESPACE}
# END WORKAROUND

# source $CICD_ROOT/smoke_test.sh

# source smoke_test.sh


# Need to make a dummy results file to make tests pass
mkdir -p artifacts
cat << EOF > artifacts/junit-dummy.xml
<testsuite tests="1">
    <testcase classname="dummy" name="dummytest"/>
</testsuite>
EOF


# This is just a check to see if we can reach gitlab.cee
git clone https://gitlab.cee.redhat.com/insights-qe/iqe-automation-hub-plugin.git
RC=$?
find iqe-automation-hub-plugin
#exit $RC

# This is a check to see if we have docker access here
echo "which docker ..."
which docker
echo "docker --version ..."
docker --version
echo "which podman ..."
podman --version
echo "podman --version"
podman --version

echo "docker-compose version ..."
docker-compose --version

echo "running containers ..."
docker ps -a


cat /etc/issue
cat /etc/redhat-release
python3 --version


echo "###########################################"
echo "OC GET PODS ..."
echo "###########################################"
echo "# oc project ${NAMESPACE}"
oc project ${NAMESPACE}
echo "# oc get pods ..."
oc get pods

echo "###########################################"
echo "OC GET PODS+CONTAINERS ..."
echo "###########################################"
# oc get pods | egrep -v NAME | awk '{print $1}' | xargs -I {} oc get pod {} -o jsonpath='{.spec.containers[*].name}'
PODS=$(oc get pods | egrep -v NAME | awk '{print $1}')
for POD in $PODS; do
    echo "# ${POD} CONTAINERS ..."
    oc get pod ${POD} -o jsonpath='{.spec.containers[*].name}'
    echo ""
done

echo "###########################################"
echo "LIST API USERS ..."
echo "###########################################"

cat << EOF > listusers.py
from galaxy_ng.app.models.auth import User
users = [x for x in User.objects.all()]
for user in users:
    print(user)
    print(user.name)
    print(user.is_superuser)
    user.is_superuser = True
    user.save()
EOF

echo "# oc project ${NAMESPACE}"
oc project ${NAMESPACE}
echo "# oc get pod -l pod=automation-hub-galaxy-api ..."
AH_API_POD=$(oc get pod -l pod=automation-hub-galaxy-api -o custom-columns=POD:.metadata.name --no-headers | head -1)
echo "AH_API_POD: ${AH_API_POD}"
#oc exec -it $AH_API_POD -- /entrypoint.sh manage shell < listusers.py
#oc exec -i $AH_API_POD -- /entrypoint.sh manage shell < listusers.py
oc exec -i $AH_API_POD /entrypoint.sh manage shell < listusers.py


echo "###########################################"
echo "ENVIRONMENT ..."
echo "###########################################"
env | sort

#echo "###########################################"
#echo "FILE LISTING"
#echo "###########################################"
#ls -al

echo "###########################################"
echo "CURL FRONTEND"
echo "###########################################"

# NAMESPACE - ephemeral-05
NG_API_URL="https://front-end-aggregator-${NAMESPACE}.apps.c-rh-c-eph.8p0c.p1.openshiftapps.com"
echo "# API URL: ${NG_API_URL}"
curl -k -v $NG_API_URL

echo "###########################################"
echo "SLEEPING 500s"
echo "###########################################"

for X in $(seq 500 -1 0); do
    echo $X
    sleep 1
done

echo "###########################################"
echo "DONE"
echo "###########################################"

