set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
source $VENVPATH/bin/activate

cd /src/galaxy_ng/

export HUB_LOCAL=1
export HUB_API_ROOT="$API_PROTOCOL://$API_HOST:$API_PORT$PULP_GALAXY_API_PATH_PREFIX"
export CONTAINER_REGISTRY="$API_HOST:$API_PORT"

export HUB_USE_MOVE_ENDPOINT=true

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

if [[ $COMPOSE_PROFILE =~ "galaxy_ng/ldap" ]]; then
    # MARKS="all or private_hub or auth_ldap"
    export HUB_TEST_AUTHENTICATION_BACKEND="ldap"
elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/keycloak" ]]; then
    # MARKS="all or private_hub or auth_keycloak"
    export HUB_TEST_AUTHENTICATION_BACKEND="keycloak"
elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/community" ]]; then
    # MARKS="all or community"
    export HUB_TEST_AUTHENTICATION_BACKEND="community"
elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/insights" ]]; then
    # MARKS="all or insights"
    export HUB_TEST_AUTHENTICATION_BACKEND="galaxy"
else 
    # MARKS="all or private_hub or auth_standalone"
    export HUB_TEST_AUTHENTICATION_BACKEND="galaxy"
fi

# echo $MARKS



# TODO: fix marks

$VENVPATH/bin/pytest -m "not cloud_only and not community_only and not rbac_roles and not iqe_rbac_test and not sync and not certified_sync and not x_repo_search and not rm_sync and not rbac_repos" $@ galaxy_ng/tests/integration
RC=$?

exit $RC
