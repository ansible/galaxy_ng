#!/usr/bin/bash

# This script is a helper for running unit tests in galaxy_ng
# It expects to be run as root inside the pulp container as created
# by the parent playbooks and role(s).

set -x
set -e

cd /src/galaxy_ng

export XDG_CONFIG_HOME=/opt/settings
#export PULP_API_ROOT="$(bash "/opt/oci_env/base/container_scripts/get_dynaconf_var.sh" API_ROOT)"
export PULP_API_ROOT="$(dynaconf get API_ROOT)"
export PULP_DATABASES__default__USER=postgres 
export PYTEST=/usr/local/bin/pytest

env | sort

PYTEST_FLAGS=""
PYTEST_FLAGS="$PYTEST_FLAGS --cov-report term-missing:skip-covered --cov=galaxy_ng"
PYTEST_FLAGS="$PYTEST_FLAGS -v -r sx --color=yes"
PYTEST_FLAGS="$PYTEST_FLAGS -p no:pulpcore"

# This command will run all unit tests in galaxy_ng/tests/unit.
# If you need to run a single test, include '-k <substring>' in the PYTEST_FLAGS variable
# If you need to get into breakpoints during unit tests, include '--capture=no' in the PYTEST_FLAGS variable
sudo -u pulp -E env "PATH=$PATH" $PYTEST $PYTEST_FLAGS --pyargs "galaxy_ng.tests.unit" "${@:2}"
