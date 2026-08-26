# AGENTS.md

Onboarding guide for AI agents working in the galaxy\_ng repository. This document covers cross-cutting conventions and architectural context. For domain-specific depth, see the guideline files listed below.

## Guideline Index

| File | Description |
|------|-------------|
| [docs/security-guidelines.md](docs/security-guidelines.md) | Access policies, RBAC systems (legacy Pulp and DAB), authentication backends, input validation, and security-related settings |
| [docs/performance-guidelines.md](docs/performance-guidelines.md) | Pulp task dispatch, resource locking, database query optimization, pagination, Redis settings cache, and transaction management |
| [docs/error-handling-guidelines.md](docs/error-handling-guidelines.md) | Custom exception handler, ValidationError usage (DRF vs Django), error formatting, logging patterns, and i18n |
| [docs/api-contracts-guidelines.md](docs/api-contracts-guidelines.md) | API version rules (v1/v3/UI v1/UI v2), viewset base classes, serializer conventions, URL routing, filtering, and backward compatibility |
| [docs/database-guidelines.md](docs/database-guidelines.md) | App label conventions, model inheritance patterns, LifecycleModel usage, migration conventions, and query patterns |
| [docs/testing-guidelines.md](docs/testing-guidelines.md) | Unit and integration test structure, BaseTestCase usage, settings overrides, mocking patterns, markers, and fixtures |
| [docs/integration-guidelines.md](docs/integration-guidelines.md) | Pulp task dispatch rules, sync patterns, signal handler conventions, external service integration, and metrics |

## Project Identity

Galaxy NG is a **Pulp plugin**, not a standalone Django application. This distinction affects nearly everything: how settings are loaded, how models inherit, how tasks run, and how URLs are registered. The Django app label is `"galaxy"`, the app lives at `galaxy_ng.app`, and it is registered as a Pulp plugin via the `pulpcore.plugin` entry point in `setup.py`.

## Repository Structure

```
galaxy_ng/
  __init__.py                     # __version__ and default_app_config
  app/
    __init__.py                   # PulpGalaxyPluginAppConfig (plugin entry point)
    settings.py                   # Settings fragment (NOT standalone Django settings)
    dynaconf_hooks.py             # Post-load hooks for conditional settings
    dynamic_settings.py           # Allowlist for runtime-overridable settings
    constants.py                  # DeploymentMode enum, PERMISSIONS dict, COMMUNITY_DOMAINS
    exceptions.py                 # ConflictError (409)
    urls.py                       # Top-level URL wiring
    models/                       # Galaxy-native models (Namespace, User, Organization, etc.)
    api/
      base.py                     # LocalSettingsMixin, base viewset/view classes
      urls.py                     # API URL assembly (v1, v3, UI v1, UI v2, content paths)
      v1/                         # Legacy roles API (models.py lives here, not in models/)
      v3/                         # Main Galaxy API (collections, namespaces, EE, tasks)
        viewsets/                  # One file per resource domain
        serializers/               # One file per resource domain
        urls.py                    # Overrides above pulp_ansible includes
      ui/
        v1/                       # UI-optimized endpoints (legacy RBAC)
        v2/                       # DAB RBAC endpoints (users, groups, orgs, teams)
    access_control/
      access_policy.py            # AccessPolicyBase and per-resource policy classes
      statements/                 # Per-deployment-mode statement dicts
        standalone.py
        insights.py
        legacy.py
        pulp.py                   # Pulp viewset URL overrides
        roles.py                  # LOCKED_ROLES definitions
    tasks/                        # Async Pulp tasks (publishing, promotion, signing, sync, etc.)
    signals/handlers.py           # Django signal handlers (loaded in AppConfig.ready())
    auth/                         # Authentication backends (session, token, keycloak, LDAP)
    shim/                         # Compatibility wrappers for DAB migration
    management/commands/           # Django management commands
    migrations/                   # Sequential migrations (0001 through 0059+)
  openapi/                        # GalaxySchemaGenerator (extends PulpSchemaGenerator)
  _vendor/                        # Vendored dependencies (automated_logging)
  tests/
    unit/                         # Unit tests (real DB, DRF APIClient)
    integration/                  # Integration tests (require running compose stack)
```

## Settings System (Dynaconf)

Galaxy NG's settings are **NOT** a normal Django settings module. The file `galaxy_ng/app/settings.py` is a settings fragment that gets merged with pulpcore's settings via Dynaconf. Key rules:

1. **Never use conditionals in settings.py** that depend on other settings keys. The final value of any key is unknown until all sources are loaded. Put conditionals in `dynaconf_hooks.py` instead.
2. **Never import settings.py directly.** Access settings through `django.conf.settings` as usual.
3. **Environment variables must use the `PULP_` prefix** (e.g., `PULP_GALAXY_DEPLOYMENT_MODE=insights`). Dynaconf handles stripping the prefix.
4. **Use `dynaconf_merge` or `dynaconf_merge_unique`** when you need to add to a list or dict rather than replace it. Appending `"dynaconf_merge"` to a list value tells Dynaconf to merge rather than overwrite.
5. **Settings loading order:** pulpcore settings.py -> galaxy_ng settings.py -> /etc/pulp/settings.py -> PULP_* env vars -> dynaconf_hooks.py post() -> database (dynamic settings).
6. The `post()` hook in `dynaconf_hooks.py` calls a series of `configure_*` functions. Each returns a dict that is merged into the final settings. Order matters -- authentication hooks must run last because they depend on outputs from earlier hooks.

## Deployment Mode Awareness

Code that behaves differently per deployment mode must check `settings.GALAXY_DEPLOYMENT_MODE` at runtime, not at import time. The three modes are:

- **standalone** (default): On-prem Automation Hub. Port 5001. Full CRUD on users/groups.
- **insights**: console.redhat.com cloud deployment. Port 8080. Uses RH Identity auth, entitlement checks.
- **community**: galaxy.ansible.com. Port 5001. GitHub OAuth, legacy roles enabled.

Access policy statements are mode-specific: `standalone.py` vs `insights.py` in `access_control/statements/`. The insights mode auto-wraps every `allow` statement with an entitlement check via `_entitelify()`.

When `RESOURCE_SERVER__URL` is set (AAP deployment), the system enters resource-server mode, which forces JWT-only auth and disables local user/group/team management. Check `settings.get("IS_CONNECTED_TO_RESOURCE_SERVER")` for this state.

## Code Style and Formatting

- **Line length:** 100 characters (enforced by both flake8 and ruff).
- **Formatter:** `darker` (not black). Only formats changed regions relative to `origin/main`. Run with `make fmt`.
- **Linters:** `flake8` (config in `flake8.cfg`) and `ruff` (config in `pyproject.toml`). Run with `make lint`.
- **Import sorting:** Handled by `isort` via darker.
- **Quote style:** Not enforced (Q000 is ignored). Both single and double quotes appear in the codebase.
- **Trailing commas:** Not enforced (COM812 is ignored).
- **Type annotations:** Not required. `RUF012` (ClassVar annotations) is ignored. Type hints appear on some function signatures but are not comprehensive.
- **f-strings vs format():** Both are acceptable. `UP032` (prefer f-strings) is explicitly ignored.
- **Test assertion style:** Both `self.assertEqual()` and bare `assert` are acceptable (PT009 is ignored).
- **Migrations:** E501 (line too long) is ignored in migration files.
- **Excluded from linting:** `galaxy_ng/_vendor/`, `galaxy_ng/app/utils/apispec/`, all `*/migrations/*`.

## Naming Conventions

### Files
- **Viewset files:** Named by resource domain, singular or descriptive (`namespace.py`, `collection.py`, `execution_environments.py`).
- **Serializer files:** Mirror viewset file names.
- **Task files:** Named by operation (`publishing.py`, `promotion.py`, `signing.py`, `deletion.py`).
- **Test files:** Prefixed with `test_` followed by the module path (`test_api_ui_user_viewset.py`, `test_api_v3_namespace.py`).
- **Management commands:** Kebab-case (`sync-galaxy-roles.py`, `create-user.py`, `task-scheduler.py`).

### Classes
- **ViewSets:** `<Resource>ViewSet` (e.g., `NamespaceViewSet`, `ContainerRepositoryViewSet`).
- **Access policies:** `<Resource>AccessPolicy` (e.g., `NamespaceAccessPolicy`).
- **Serializers:** `<Resource>Serializer` for detail, `<Resource>SummarySerializer` for list views.
- **Filters:** `<Resource>Filter` (e.g., `NamespaceFilter`, `UserViewFilter`).
- **Models:** Singular nouns (`Namespace`, `CollectionImport`, `ContainerRegistryRemote`).

### Variables and Settings
- **Galaxy-specific settings:** Prefixed with `GALAXY_` (e.g., `GALAXY_DEPLOYMENT_MODE`, `GALAXY_FEATURE_FLAGS`).
- **DAB settings:** Prefixed with `ANSIBLE_BASE_` (e.g., `ANSIBLE_BASE_RBAC_MODEL_REGISTRY`).
- **Logger instances:** `log = logging.getLogger(__name__)` for most modules. Exception: legacy role import uses a descriptive name.

## Import Conventions

The codebase follows a consistent import ordering pattern (enforced by isort through darker):

1. Standard library imports
2. Third-party imports (Django, DRF, pulpcore, pulp\_ansible, pulp\_container, django\_filters, etc.)
3. Local application imports (`galaxy_ng.app.*`)

Within Galaxy NG code, the common import aliases are:

```python
from galaxy_ng.app.api import base as api_base        # For base viewset/view classes
from galaxy_ng.app.api.v3 import serializers           # For v3 serializers
from galaxy_ng.app import models                       # For Galaxy models
from galaxy_ng.app.constants import DeploymentMode     # For deployment mode checks
```

Pulp models are imported directly from their plugin packages:
```python
from pulpcore.plugin import models as core_models
from pulp_ansible.app import models as ansible_models
from pulp_container.app import models as container_models
```

## Architectural Patterns

### Pulp Plugin System

Galaxy NG registers itself as a Pulp plugin via the `pulpcore.plugin` entry point in `setup.py`. The `PulpGalaxyPluginAppConfig` in `galaxy_ng/app/__init__.py` is the entry point. Its `ready()` method:
1. Imports signal handlers (must happen here, not at module level elsewhere).
2. Registers additional models with DAB's permission registry.
3. Patches upstream models to satisfy DAB system checks.

### Two RBAC Systems

This is critical to understand. The codebase has **two coexisting permission systems**:

1. **Legacy Pulp RBAC** (v1, v3, UI v1 endpoints): Statement-based access policies in `access_control/statements/`. Uses `AccessPolicyBase` and `pulpcore.plugin.util.assign_role`/`remove_role`.
2. **DAB RBAC** (UI v2 endpoints): Uses `AnsibleBaseObjectPermissions` and `permission_registry.is_registered()`. Models must be in `ANSIBLE_BASE_RBAC_MODEL_REGISTRY`.

These systems are kept in sync via signal handlers in `signals/handlers.py`. The sync uses re-entrancy guards (`rbac_signal_in_progress()`) to prevent infinite loops.

### ViewSet Base Class Rules

Each API version has its own base class inheritance. Mixing them is a bug:

| API Version | Base Classes | Source |
|------------|-------------|--------|
| v3, UI v1 | `api_base.ModelViewSet`, `api_base.ViewSet`, etc. | `galaxy_ng/app/api/base.py` |
| UI v2 | `BaseViewSet(viewsets.ModelViewSet)` | `galaxy_ng/app/api/ui/v2/views.py` |
| v1 (legacy) | Bare DRF `viewsets.ModelViewSet` | Direct DRF import |
| Pulp extension | `LocalSettingsMixin` + Pulp viewset | Mixed inheritance |

The `LocalSettingsMixin` provides Galaxy's authentication classes, pagination, exception handler, and a `_MustImplementPermission` guard. Every v3/UI v1 viewset **must** declare `permission_classes` or it raises `NotImplementedError` at runtime.

### URL Override Pattern

When Galaxy NG needs to override a pulp\_ansible endpoint, the override is placed **above** `path("", include(v3_urls))` in `galaxy_ng/app/api/v3/urls.py`. Django uses the first matching URL, so Galaxy's version takes precedence. Comments in that file explain why each override exists.

### v1 Legacy Code Lives Outside models/

Legacy role models (`LegacyNamespace`, `LegacyRole`, `LegacyRoleTag`, etc.) are defined in `galaxy_ng/app/api/v1/models.py`, not in `galaxy_ng/app/models/`. They still use the `"galaxy"` app label and standard Django migrations.

### Feature-Gated URL Paths

URL paths for optional features are conditionally included based on `settings.GALAXY_FEATURE_FLAGS`:

```python
if settings.GALAXY_FEATURE_FLAGS['execution_environments']:
    paths.append(path('execution-environments/', include(container_paths)))
```

New feature endpoints should follow this pattern rather than always being registered.

## Common Pitfalls

### 1. Wrong ValidationError import
Using `django.core.exceptions.ValidationError` in API views or serializers causes unformatted 500 errors because the custom exception handler only handles `rest_framework.exceptions.ValidationError`. See `docs/error-handling-guidelines.md` for the full rules.

### 2. Settings conditionals in the wrong file
Putting `if SOME_SETTING:` logic in `settings.py` is unreliable because other settings sources have not been loaded yet. All conditional settings logic must go in `dynaconf_hooks.py`.

### 3. Mixing viewset base classes across API versions
UI v2 viewsets must not inherit from `api_base` classes (they use DAB's pagination and permissions). v3/UI v1 viewsets must not use bare DRF base classes (they would lose Galaxy's auth, pagination, and exception handling). See `docs/api-contracts-guidelines.md` for the base class table and extension patterns.

### 4. Forgetting resource locks on task dispatch
Pulp tasks that mutate repositories must declare `exclusive_resources`. Forgetting this allows concurrent mutations that corrupt repository state. See `docs/performance-guidelines.md` for lock patterns.

### 5. Direct model imports in migrations
Always use `apps.get_model("galaxy", "ModelName")` in data migrations, never direct model imports. The model class at migration time may differ from the current code. See `docs/database-guidelines.md` for migration conventions.

### 6. Proxy model permission assignment
Pulp does not support role assignment on proxy models. The access control mixins resolve to the concrete model via `_meta.concrete_model` before assigning permissions. If you add a new proxy model with RBAC, make sure to follow this pattern. See `docs/database-guidelines.md` for proxy model patterns and `docs/security-guidelines.md` for RBAC system details.

### 7. Signal handler re-entrancy
RBAC signal handlers that sync between Pulp and DAB must check `rbac_signal_in_progress()` at the top to prevent infinite loops. Always use the `pulp_rbac_signals()` or `dab_rbac_signals()` context managers to mark the origin of a change. See `docs/integration-guidelines.md` for signal handler conventions.

### 8. Exposing Pulp field names in API responses
Pulp timestamp fields (`pulp_created`, `pulp_last_updated`) must be remapped to `created_at` and `updated_at` in serializers. Do not expose `pulp_*` field names. See `docs/api-contracts-guidelines.md` for serializer conventions.

### 9. Forgetting `on_commit=True` on lifecycle hooks with side effects
LifecycleModel hooks that perform cache invalidation or dispatch external calls must use `on_commit=True` to ensure they only fire after the transaction commits. See `docs/database-guidelines.md` for LifecycleModel hook patterns.

### 10. Version tracked in three places
The version string is maintained in `galaxy_ng/__init__.py`, `galaxy_ng/app/__init__.py`, and `setup.py`. All three must stay in sync. Use `make dev/bumpversion-*` (which uses bump-my-version) to update them atomically.

## CI/CD

The main CI workflow is `.github/workflows/ci-docker-compose-integration.yml`. It runs on every PR and push to `main`/`stable-*`. It spins up each deployment profile (standalone, insights, community, certified-sync) and runs the corresponding pytest markers:

| Profile | Markers |
|---------|---------|
| standalone | `deployment_standalone or all`, `x_repo_search`, `iqe_rbac_test`, `rbac_parallel_group_1`, `rbac_parallel_group_2` |
| insights | `deployment_cloud or all` |
| community | `deployment_community` |
| certified-sync | `sync` |

All test invocations pass `-p 'no:pulpcore' -p 'no:pulp_ansible'` to disable upstream pytest plugin hooks.

The CI also checks for a DAB branch override in PR descriptions (`.ci/scripts/get_dab_for_pr.py`) to allow testing against unreleased DAB changes.

## Dependency Management

Dependencies are declared in `setup.py` (`install_requires`) with pinned versions. Lock files live in `requirements/` and are generated with `pip-compile`.

### Make Targets

| Target | Usage |
|--------|-------|
| `make requirements/no-pip-upgrade` | Regenerate lock files from `setup.py` and `*.in` files without upgrading packages |
| `make requirements/pip-upgrade-single-package package=<name>` | Upgrade a single package (e.g., `package=django`) |
| `make requirements/pip-upgrade-multiple-packages packages="<pkg1> <pkg2>"` | Upgrade multiple packages at once |
| `make requirements/pip-upgrade-all` | Upgrade all packages to latest compatible versions |

### Workflow

1. Edit the version pin in `setup.py` under `install_requires`.
2. Run the appropriate `make requirements/*` target to regenerate the lock files (`requirements.common.txt`, `requirements.insights.txt`, `requirements.standalone.txt`).
3. Deployment-specific extras go in `requirements/requirements.insights.in` or `requirements/requirements.standalone.in`.

## Internationalization

Wrap all user-facing error messages and UI strings in `gettext_lazy`:

```python
from django.utils.translation import gettext_lazy as _

raise ValidationError(detail={'name': _('Name must be longer than 2 characters')})
```

This is consistently applied across serializers, views, and constants. The repo supports English (default), Japanese, Korean, Dutch, French, Spanish, and Chinese.
