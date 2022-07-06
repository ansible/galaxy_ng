# Running integration tests
Integration tests are expected to be called via [galaxy_ng/dev/common/RUN_INTEGRATION.sh](https://github.com/ansible/galaxy_ng/blob/master/dev/common/RUN_INTEGRATION.sh)
  - `make docker/test/integration`
  - `make docker/test/integration/container`
- Run in PR via GitHub Actions ci_standalone.yml for `DEPLOYMENT_MODE=standalone`
- Run in PR via pr_check.sh in an ephemeral environment for `DEPLOYMENT_MODE=insights`

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
