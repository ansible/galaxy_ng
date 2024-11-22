# Integration tests
(*To run integration tests with docker compose stack, check the [Running integration tests](../galaxy_ng/tests/integration/README.md)*) 

## GitHub Actions

GitHub Actions scripts for integration tests are all defined under `/dev/oci_env_integration/actions`. These are all python files that use the `action_lib.py` library to spin up an oci-env environment and run tests on it.

Example script:

```python
import action_lib

env = action_lib.OCIEnvIntegrationTest(
    envs=[
        {
            "env_file": "standalone.compose.env",
            "run_tests": True,
            "db_restore": None,
            "pytest_flags": '-m sync'
        },
        {
            "env_file": "sync-test.compose.env",
            "run_tests": False,
            "db_restore": "insights-fixture",
            "pytest_flags": None
        }
    ]
)
```

`action_lib` provides the OCIEnvIntegrationTest class that takes in a list of environments which are used to run tests. The environment configuration works as follows:

```
envs: list of environment definitions to spin up for testing. Environment
definitions accept the following args:

    env_file (string, required): oci-env env file to use for the tests. These are all loaded
        from dev/oci_env_integration/oci_env_configs
    run_tests (boolean, required): if true, integration tests will be run inside this instance
    db_restore (string, optional): database backup to restore before running tests These are all
        loaded from dev/oci_env_integration/oci_env_configs. When defining this, omit
        the file extension (ex: fixture, not fixtur.tar.gz)
    pytest_flags (string, optional): flags to pass to pytest when running integration tests.
        oci-env automatically identifies which pytest marks to apply to tests based
        on the environment that's running, however in some cases you may want to
        override this if the test is meant to only apply to a subset of tests (such as rbac)
    wait_before_tests (int, optional): some environments need some extra time set-up configs
        that oci-env poll can't monitor. This will cause the environment to wait the given
        number of seconds before running integration tests after the stack has spun up.
```

To set up a new GitHub Action: 

1. create a new script in the `actions/` directory

2. define a Makefile command for it like this:

```
.PHONY: gh-action/certified-sync
gh-action/certified-sync:
	python3 dev/oci_env_integration/actions/certified-sync.py
```

3. add the new action to `/.github/workflows/ci_oci-env-integration.yml` like so:


```
jobs:
  integration:
    strategy:
      fail-fast: false
      matrix:
        env:
          - TEST_PROFILE: ldap
          - TEST_PROFILE: keycloak
          - TEST_PROFILE: standalone
          - TEST_PROFILE: rbac
          - TEST_PROFILE: certified-sync  <-----------------------
          - TEST_PROFILE: insights
          - TEST_PROFILE: iqe_rbac
          - TEST_PROFILE: x_repo_search
```

## Marks

Tests are typically written for one of three potential deployment modes:

1. cloud/insights mode
2. community
3. standalone

To have a test run in one of these categories, you can include the `deployment_cloud`, `deployment_community` or `deployment_standalone` marks on your tests.

Tests that are intended to pass on any deployment mode should be marked with `all`. By default unmarked tests will receive the `all` mark`.

All `deployment_standalone` tests are also expected to pass when running with ldap or keycloak authentication. If a test is meant to test a specific authentication backend, use the `ldap` or `keycloak` marks, and remove `deployment_standalone`.

## Integration tests configuration

Integration tests are configured using environment variables. These variables are set in the oci-env profiles configuration so that integration tests for the profile you're running should work out of the box. Here's an example of the settings that the base profile uses:

```
# Integration test settings
HUB_API_ROOT={API_PROTOCOL}://{API_HOST}:{API_PORT}/api/galaxy/
CONTAINER_REGISTRY={API_HOST}:{API_PORT}
HUB_LOCAL=1
HUB_USE_MOVE_ENDPOINT=true
HUB_TEST_AUTHENTICATION_BACKEND=galaxy
HUB_TEST_MARKS=deployment_standalone or all
```
