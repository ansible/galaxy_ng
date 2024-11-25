# Running integration tests
Based on running docker compose stack deployment mode (standalone, community, insights), install requirements, set environment variables and markers on the host:


Install `integration_requirements.txt` in your virtual env
```
python3 -m venv gng_int_testing
source gng_testing/bin/activate
pip install -r integration_requirements.txt
```

## Standalone
```
export HUB_API_ROOT='http://localhost:5001/api/galaxy/'
export HUB_LOCAL=1
```

```python
pytest -v -r sx --color=yes -m 'deployment_standalone' galaxy_ng/tests/integration
```

## Community
```
export HUB_API_ROOT='http://localhost:5001/api/'
export HUB_LOCAL=1
```

run tests:
```python
pytest -v -r sx --color=yes -m 'deployment_community' galaxy_ng/tests/integration
```

## Insights (cloud)
```
export HUB_API_ROOT="http://localhost:8080/api/automation-hub/"
export HUB_AUTH_URL="http://localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token"
export HUB_USE_MOVE_ENDPOINT="true"
export HUB_UPLOAD_SIGNATURES="true"
```

run tests:
```python
pytest -v -r sx --color=yes -m 'deployment_cloud or all' galaxy_ng/tests/integration
```

or specify test you would like to run: 
```python
pytest -v -r sx --color=yes -k ' test_delete_collection' galaxy_ng/tests/integration
```

Tests that are intended to pass on any deployment mode should be marked with `all`. By default unmarked tests will receive the `all` mark`.
All `deployment_standalone` tests are also expected to pass when running with ldap or keycloak authentication. If a test is meant to test a specific authentication backend, use the `ldap` or `keycloak` marks, and remove `deployment_standalone`.
List of all marks in [conftest.py](conftest.py)



# Test Data
* Test data is defined in [galaxy_ng/dev/common/setup_test_data.py](https://github.com/ansible/galaxy_ng/blob/master/dev/common/setup_test_data.py) and includes namespaces, users, tokens, and groups
* This data is used for all ways the integration tests are run
* Note: this script is also called by default when manual ephemeral environments are spun up, via `ahub.sh`

# User Profiles
* User profiles are defined in [galaxy_ng/tests/integration/conftest.py](https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/tests/integration/conftest.py)
* Usernames are different than the profile name, check `conftest.py` for usernames and passwords
* Usernames and passwords match the ephemeral enviornment Keycloak SSO, so the same test data is used for `DEPLOYMENT_MODE=standalone` and `DEPLOYMENT_MODE=insights`

## User Profile List
* `basic_user` user with only permissions on a namespace for upload
* `partner_engineer` user with permissions to add namespaces, groups, users, and approve content from `staging` repo into `published` repo
* `org_admin` outside our app in ephemeral environments the Keycloak SSO defines this user as an Organization Admin for a customer account, used with for `DEPLOYMENT_MODE=insights`
* `admin` a django superuser, to be used sparingly in tests
