set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
source $VENVPATH/bin/activate

cd /src/galaxy_ng/

django-admin shell < ./dev/common/setup_test_data.py
cd galaxy_ng
django-admin makemessages --all

cd /src/galaxy_ng/

# Mark taxonomy:

# would be good to be able to just get rid of these entirely
# - `auth_ldap` -> tests specific to ldap authentication
# - `auth_keycloak` -> tests specific to keycloak authentication
# - `auth_standalone` -> tests specific to standalone

# - `deployment_all` -> run test in all environments
# - `deployment_private_hub` -> tests specific to private hub (EEs, private features)
# - `deployment_insights` -> tests specific to insights mode (synclists, RH auth)
# - `deployment_community` -> tests specific to community (GH auth, legacy roles, legacy namespaces)
# - `rbac` -> rbac roles tests
# - `sync` -> requires external service to sync from



# check the environment to see if the test fixtures are set up. If they aren't,
# initialize them

# if [[ $COMPOSE_PROFILE =~ "galaxy_ng/ldap" ]]; then
#     MARKS="all or private_hub or auth_ldap"
# elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/keycloak" ]]; then
#     MARKS="all or private_hub or auth_keycloak"
# elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/community" ]]; then
#     MARKS="all or community"
# elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/insights" ]]; then
#     MARKS="all or insights"
# else 
#     MARKS="all or private_hub or auth_standalone"
# fi

# echo $MARKS



# TODO: fix marks
set -x

$VENVPATH/bin/pytest -v -r sx --color=yes -m "$HUB_TEST_MARKS" "$@" galaxy_ng/tests/integration
RC=$?

exit $RC
