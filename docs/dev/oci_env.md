# Run Galaxy NG using oci-env

## Setting up your environment

Follow the instructions provided from the [oci-env repository](https://github.com/pulp/oci_env#getting-started). When you set up your compose.env file, use this one:

```
# : separated list of profiles to use. Ex: galaxy_ng/base:galaxy_ng/ui
COMPOSE_PROFILE=galaxy_ng/base

# : separate list of python dependencies to include from source
DEV_SOURCE_PATH=galaxy_ng

# Program to use for compose. This defaults to podman. Uncomment this to use docker-compose.
COMPOSE_BINARY=docker

# Set any custom pulp settings by adding environment variables with the PULP_ prefix
# PULP_MY_SETTING....

# Django admin user credentials that gets created during startup
# DJANGO_SUPERUSER_USERNAME=admin
# DJANGO_SUPERUSER_PASSWORD=password

# Port, hostname and protocol used to configure pulp content origin
# API_HOST=localhost
# API_PORT=5001
# API_PROTOCOL=http
```

This will launch galax_ng from source (see `DEV_SOURCE_PATH`) using the galaxy_ng/base profile (see `COMPOSE_PROFILE`). You can get more information on the options that are available for this profile with `oci-env profile docs galaxy_ng/base`.

Other profiles are available under the `profiles/` directory.

## Develop using keycloak, insights mode and ldap

Profiles for all of these modes are available from galaxy_ng. Simply add them to your `COMPOSE_PROFILE`:

```
# compose.env

# LDAP
COMPOSE_PROFILE=galaxy_ng/base:galaxy_ng/ldap

# Insights
COMPOSE_PROFILE=galaxy_ng/base:galaxy_ng/insights

# Keycloak
COMPOSE_PROFILE=galaxy_ng/base:galaxy_ng/keycloak
```

More documentation for each of these profiles can be found in their respective README files or by using the `oci-env profile docs` command.

## Testing

### Integration

To run the tests against your currently environment cd to your galaxy_ng folder and run `make oci-env/integration`. This will run the integration tests that are expected to pass for the profile that you have configured. The tests should be smart enough to determine if you have a customized url or port for galaxy ng. This accepts a FLAGS arg, which allows you to send custom pystest flags such as `make oci-env/integration FLAGS="-m rbac_roles -k test_admin_permissions"`. The `-k` flag is especially useful as it lets you pick specific tests by name or by filename.

To run the same tests that run in github actions, run `make gh-action/<action>` (ex `make gh-action/standalone`). See the Makefile for all the supported targets. This will spin up the stack in the same way that GitHub actions does and run the same set of tests that the CI pipeline does. This command will take care of provisioning the whole environment, running tests and tearing down the environment.

`make gh-action/*` accepts the following environment variables:

- `GH_DUMP_LOGS=1` -> print the server logs after the tests are finished running
- `GH_TEARDOWN=0` -> don't teardown the environment after the tests exit. This allows you to rerun the action without having to wait for the environment to be re provisioned every time.
- `GH_FLAGS="pytest flags"` -> allows you to pass custom pytest flags to the integration tests.

Example: `GH_FLAGS="-k test_delete_collection" GH_DUMP_LOGS=1 GH_TEARDOWN=0 make gh-action/standalone`

### Functional and Unit

See the [oci-env README](https://github.com/pulp/oci_env#running-tests) for information on running unit and functional tests.
