set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
source $VENVPATH/bin/activate

cd /src/galaxy_ng/

django-admin shell < ./dev/common/setup_test_data.py
cd galaxy_ng
django-admin makemessages --all

cd /src/galaxy_ng/



set -x

export HUB_API_ROOT=http://jwtproxy:8080/api/galaxy/
# export HUB_ADMIN_PASS=admin
export HUB_USE_MOVE_ENDPOINT=1
export HUB_LOCAL=1
export ENABLE_DAB_TESTS=1
export HUB_TEST_MARKS="deployment_standalone and not skip_in_gw"
export JWT_PROXY=true
export AAP_GATEWAY=true
export GW_ROOT_URL=http://jwtproxy:8080

#$VENVPATH/bin/pytest -v -r sx --color=yes "$@" galaxy_ng/tests/integration/dab
$VENVPATH/bin/pytest -v -r sx --color=yes -m "$HUB_TEST_MARKS" "$@" galaxy_ng/tests/integration
RC=$?

exit $RC
