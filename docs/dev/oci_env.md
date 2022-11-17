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

You can find environment configurations for running integration tests in each deployment mode under dev/oci_env_configs/. Some extra settings to accommodate the testing are provided there.

Once the environment is running, run the tests as you would for the [docker environment](/galaxy_ng/dev/docker_environment/#integration-tests).

### Functional and Functional

See the [oci-env README](https://github.com/pulp/oci_env#running-tests) for information on running unit and functional tests.
