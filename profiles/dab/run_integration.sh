set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
if  [[ ! -d $VENVPATH ]]; then
    virtualenv --python=$(which python3.11) $VENVPATH
    $PIP install -r integration_requirements.txt
    if [[ -d ../galaxykit ]]; then
        cd ..
        $PIP install -e galaxykit
        cd galaxy_ng
    fi

fi
source $VENVPATH/bin/activate

set -x

export HUB_API_ROOT=https://localhost/api/galaxy/
# export HUB_ADMIN_PASS=admin
export HUB_USE_MOVE_ENDPOINT=1
export HUB_LOCAL=1
export ENABLE_DAB_TESTS=1
export HUB_TEST_MARKS="(deployment_standalone or x_repo_search or all) and not package and not iqe_ldap and not skip_in_gw"
export AAP_GATEWAY=true
export AAP_GATEWAY_ADMIN_USERNAME=admin
export AAP_GATEWAY_ADMIN_PASSWORD=admin
export GW_ROOT_URL=https://localhost
export CONTAINER_REGISTRY=localhost

export GALAXYKIT_SLEEP_SECONDS_POLLING=.5
export GALAXYKIT_SLEEP_SECONDS_ONETIME=.5
export GALAXYKIT_POLLING_MAX_ATTEMPTS=50
export GALAXY_SLEEP_SECONDS_POLLING=.5
export GALAXY_SLEEP_SECONDS_ONETIME=.5
export GALAXY_POLLING_MAX_ATTEMPTS=50


$VENVPATH/bin/python profiles/dab/make_test_data.py
docker exec -it ci-dab-pulp-1 bash -c \
    'pulpcore-manager shell -c "from galaxy_ng.app.models.auth import Group; Group.objects.get_or_create(name=\"ship_crew\")"'

$VENVPATH/bin/pytest --log-level=DEBUG -v -r sx --color=yes -m "$HUB_TEST_MARKS" "$@" galaxy_ng/tests/integration
RC=$?

exit $RC
