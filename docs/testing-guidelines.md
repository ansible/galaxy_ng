# Testing Guidelines

## Running Tests

### Unit Tests
```bash
make test/unit          # Runs tox -e py312
tox -e py312            # Equivalent direct call

# Single test file or function
pytest galaxy_ng/tests/unit/path/to/test_file.py::TestClass::test_method \
    -p 'no:pulpcore' -p 'no:pulp_ansible'
```

Tox automatically starts a PostgreSQL container on port 5433, creates `/tmp/pulp` directories,
generates an encryption key, and installs local sibling checkouts (`../django-ansible-base`,
`../pulpcore`, etc.) if present.

Unit tests use `-p 'no:pulpcore' -p 'no:pulp_ansible'` to disable those plugins' pytest hooks.

### Integration Tests
Require a running docker compose stack (`make compose/standalone`, etc.).

```bash
make test/integration/standalone    # -m 'deployment_standalone or all'
make test/integration/community     # -m 'deployment_community'
make test/integration/insights      # -m 'deployment_cloud or all'
make test/integration/certified     # -m 'sync'
```

Integration tests also use `-p 'no:pulpcore' -p 'no:pulp_ansible'` to disable those plugins' pytest hooks.

## Coverage

```bash
# Run tests with coverage
tox -e py312 -- --cov=galaxy_ng

# Generate HTML report locally
pytest --cov=galaxy_ng --cov-report=html
```

**Coverage Targets:**
- Maintain >70% coverage on new code
- CI uploads coverage to both SonarCloud and Codecov

**Coverage Tools:**
- **SonarCloud**: Public metrics, quality gates, code analysis ([view](https://sonarcloud.io/summary/new_code?id=ansible_galaxy_ng))
- **Codecov**: Detailed line-by-line coverage tracking ([view](https://app.codecov.io/github/ansible/galaxy_ng))

**Exclusions** (aligned across `codecov.yml` and `sonar-project.properties`):
- Tests, migrations, v1 API (deprecated), management commands, vendored code

## Unit Test Structure

### Base Class: `BaseTestCase`

Most API-level unit tests extend `BaseTestCase` (in `galaxy_ng/tests/unit/api/base.py`),
which provides:

- DRF `APIClient` setup with `force_authenticate`
- `_create_user(username)`, `_create_group(scope, name, users, roles)`,
  `_create_namespace(name, groups)`, `_create_partner_engineer_group()`
- A mocked `_get_rh_identity` for access policy checks (always returns an entitled org admin)

```python
from .base import BaseTestCase, get_current_ui_url, MockSettings

class TestMyViewSet(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='admin', is_superuser=True)
        self.client.force_authenticate(user=self.admin_user)
```

### When to Use TestCase vs Bare Functions

- **API viewset tests**: Use `BaseTestCase` (inherits DRF `APITestCase`). The real database
  is used via Django's test transaction rollback.
- **Pure logic / utility tests**: Use `django.test.TestCase` directly.
- **Tests that need heavy module mocking** (e.g., signal handler tests): Use bare pytest
  functions with `@pytest.fixture(autouse=True)` to mock `sys.modules`. Because autouse
  fixtures run after test-module collection (not before top-level imports), do **not** import
  the module under test at the top of the file. Instead, import it inside each test function
  or fixture body after the `sys.modules` mock is installed. See
  `galaxy_ng/tests/unit/signals/test_handlers.py` for the canonical pattern. If the mock must
  be active before any import in the module tree, place it in a `conftest.py` in the test
  directory where pytest evaluates it during collection.
- **Dynaconf hook tests**: Use pytest functions with parametrize; the `SuperDict` mock in
  `test_dynaconf_hooks.py` simulates Dynaconf's settings object.

## Settings Overrides

There are **three** patterns for changing Django settings in unit tests. Use the right one:

| Pattern | When to Use |
|---------|------------|
| `@override_settings(KEY=value)` on class/method | Deployment mode, feature toggles that Django reads directly |
| `with self.settings(KEY=value):` inside a test method | Same as above, but scoped to a block |
| `with patch('module.settings', MockSettings({...})):` | When code reads settings via a local `settings` import (Dynaconf-style); does NOT go through Django's settings machinery |

`MockSettings` (from `base.py`) is a dict-like shim that sets attributes for each key.
Use it when the code under test accesses `settings.SOME_KEY` as a property rather than
through `django.conf.settings`.

The most common override is deployment mode:
```python
@override_settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value)
```

## Mocking Patterns

### What to Mock
- **Pulp dispatched tasks**: Mock `dispatch`, `add_and_remove`, `sign` when testing task
  orchestration logic (see `test_promotion.py`).
- **External services**: `SyncExecutor`, `aiohttp.ClientSession`, `HttpDownloader`.
- **Settings object**: When testing dynaconf hooks or code that reads settings as attributes.
- **Django signals senders**: When testing signal handlers in isolation.

### What NOT to Mock
- **Django ORM in API tests**: `BaseTestCase` uses the real database. Create real model
  instances (`User.objects.create`, `Namespace.objects.create`, etc.).
- **DRF request/response cycle**: Use `self.client.get/post/put/patch/delete` against real URLs.
- **Access policies**: The `BaseTestCase` already mocks `_get_rh_identity`; do not add extra
  access policy mocks unless testing a specific auth scenario.

### Common Mock Targets
```python
# Mock settings read as a property
@patch('galaxy_ng.app.pipelines.settings')

# Mock a queryset chain
@patch('galaxy_ng.app.tasks.promotion.AnsibleRepository.objects.filter')

# Mock the resource server setting
@override_settings(RESOURCE_SERVER=None)
```

## Integration Test Conventions

### Markers
Every integration test must have at least one deployment marker. Tests without any marker
automatically receive the `all` marker (runs in standalone and insights modes).

Key markers:
- `deployment_standalone` -- standalone-only tests
- `deployment_cloud` -- insights/cloud-only tests
- `deployment_community` -- community-only tests
- `all` -- auto-applied to unmarked tests; runs in standalone + insights
- `min_hub_version("4.10")` / `max_hub_version("4.7")` -- version-gated tests
- `skip_in_gw` -- skip when hub is behind the gateway

The `qa` marker is optionally used to tag tests for specific CI jobs (e.g., vortex). It is not required for all integration tests.

### User Profiles
Integration tests authenticate via named profiles defined in
`galaxy_ng/tests/integration/constants.py` (`PROFILES`, `CREDENTIALS`).
Access them through the `galaxy_client` session fixture:

```python
def test_example(galaxy_client):
    gc = galaxy_client("admin")          # superuser
    gc = galaxy_client("basic_user")     # non-privileged user
    gc = galaxy_client("partner_engineer")  # collection/user/group admin
```

### Key Fixtures (session-scoped)
| Fixture | Purpose |
|---------|---------|
| `ansible_config` | Returns the environment's `AnsibleConfigFixture` |
| `galaxy_client` | Factory returning a `GalaxyClient` authenticated as a profile |
| `hub_version` | The running hub version string |
| `settings` | Dict of `_ui/v1/settings/` from the running instance |
| `artifact` | Builds a randomized collection tarball (not published) |

### Helpers
- `galaxykit` -- primary client library for integration tests (`GalaxyClient`)
- `galaxy_ng.tests.integration.utils` -- `build_collection`, `set_certification`,
  `ansible_galaxy`, `get_client`, `upload_artifact`
- `galaxy_ng.tests.integration.utils.iqe_utils` -- `GalaxyKitClient`,
  `is_standalone`, `is_ephemeral_env`, `aap_gateway`, `get_hub_version`
- `galaxy_ng.tests.integration.utils.tools` -- `generate_random_string`,
  `generate_random_artifact_version`

## Test Data Setup

### Unit Tests

Create objects directly via Django ORM in `setUp`:
```python
self.namespace = models.Namespace.objects.create(name='test_ns')
self.repo = AnsibleRepository.objects.create(name='test_repo')
AnsibleDistribution.objects.create(name='test_repo', base_path='test_repo', repository=self.repo)
```

### Integration Tests
Use `galaxykit` methods or direct API calls. Always clean up created resources
(use fixtures with `yield` + teardown, or `request.addfinalizer`).

## Dynaconf Hook Testing

The `test_dynaconf_hooks.py` file is the largest unit test file (~2000 lines).
It uses two custom mocks instead of Django's settings:

- **`SuperDict`**: A dict subclass that behaves like Dynaconf's settings object
  (supports `.set()`, attribute access, `.as_dict()`, `._store`).
- **`SuperValidator`**: A no-op validator mock.
- **`BASE_SETTINGS`**: A template dict merged with test-specific overrides.

Pattern for testing hook functions:
```python
@pytest.mark.parametrize("do_stuff, extra_settings, expected_results", [...])
def test_dynaconf_hooks_authentication_backends_and_classes(do_stuff, extra_settings, expected_results):
    settings = SuperDict({**BASE_SETTINGS, **extra_settings})
    result = configure_socialauth(settings)
```

## File Organization

```text
galaxy_ng/tests/
  unit/
    api/                  # Viewset tests (use BaseTestCase)
      base.py             # BaseTestCase, MockSettings, MOCKED_RH_IDENTITY
      rh_auth.py          # Helper to build x-rh-identity headers
      synclist_base.py    # Base for synclist viewset tests
      test_api_ui_*.py    # UI API endpoint tests
      test_api_v3_*.py    # V3 API endpoint tests
    app/                  # Non-API application logic tests
      auth/               # Auth backend tests (LDAP, keycloak, token)
      common/             # OpenAPI schema tests
      management/         # Management command tests
      metrics_collection/ # Analytics collector tests
      tasks/              # Async task tests (heavy mocking)
      utils/              # Utility function tests
    signals/              # Signal handler tests (mock sys.modules)
    test_models.py        # Model-level tests (real DB)
    test_settings.py      # DAB settings integration check
  integration/
    api/                  # REST API integration tests
    aap/                  # AAP-specific (RBAC, user management)
    cli/                  # ansible-galaxy CLI tests
    community/            # Community deployment tests
    dab/                  # DAB RBAC integration tests
    ui/                   # Selenium UI tests
    utils/                # Shared helpers and client wrappers
    conftest.py           # Markers, session fixtures, profile setup
    constants.py          # Profiles, credentials, polling constants
```

## Linting

Tests must pass `flake8` (line length 100, config in `flake8.cfg`) and `ruff` (config in
`pyproject.toml`). PT009 (unittest-style asserts) is intentionally ignored because the
codebase mixes `self.assertEqual` and bare `assert`. Both styles are acceptable.
