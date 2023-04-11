set -e

VENVPATH=/tmp/gng_testing
PIP=${VENVPATH}/bin/pip
source $VENVPATH/bin/activate

cd /src/galaxy_ng/

export HUB_LOCAL=1
export HUB_API_ROOT="$API_PROTOCOL://$API_HOST:$API_PORT$PULP_GALAXY_API_PATH_PREFIX"

export HUB_USE_MOVE_ENDPOINT=true


# Mark taxonomy:
# - `all` -> run test in all environments
# - `private_hub` -> tests specific to private hub (EEs, private features)


# would be good to be able to just get rid of these entirely
# - `auth_ldap` -> tests specific to ldap authentication
# - `auth_keycloak` -> tests specific to keycloak authentication
# - `auth_standalone` -> tests specific to standalone



# - `insights` -> tests specific to insights mode (synclists, RH auth)
# - `community` -> tests specific to community (GH auth, legacy roles, legacy namespaces)
# - `rbac` -> rbac roles tests
# - `sync` -> requires external service to sync from




# check the environment to see if the test fixtures are set up. If they aren't,
# initialize them

if [[ $COMPOSE_PROFILE =~ "galaxy_ng/ldap" ]]; then
    MARKS="all or private_hub or auth_ldap"
    export HUB_TEST_AUTHENTICATION_BACKEND="ldap"
elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/keycloak" ]]; then
    MARKS="all or private_hub or auth_keycloak"
    export HUB_TEST_AUTHENTICATION_BACKEND="ldap"
elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/community" ]]; then
    MARKS="all or community"
    export HUB_TEST_AUTHENTICATION_BACKEND="community"
elif [[ $COMPOSE_PROFILE =~ "galaxy_ng/insights" ]]; then
    MARKS="all or insights"
    export HUB_TEST_AUTHENTICATION_BACKEND="galaxy"
else 
    MARKS="all or private_hub or auth_standalone"
    export HUB_TEST_AUTHENTICATION_BACKEND="galaxy"
fi

echo $MARKS

$VENVPATH/bin/pytest --capture=no -m "$MARKS" $@ galaxy_ng/tests/integration
RC=$?

exit $RC
