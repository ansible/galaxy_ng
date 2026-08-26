# Security Guidelines

## Access Policy Architecture

### Statement-Based Access Control

Every viewset should declare a `permission_classes` attribute pointing to an `AccessPolicyBase` subclass. The base classes in `galaxy_ng/app/api/base.py` (`APIView`, `ViewSet`, `ModelViewSet`, etc.) enforce this by setting a default `_MustImplementPermission` that raises `NotImplementedError` if not overridden. Views may explicitly set `permission_classes = []` to disable permission checks (e.g., `NotFoundView`), but this should be rare and intentional.

Access policies are defined as statement lists in `galaxy_ng/app/access_control/statements/`. There are three layers:

1. **Galaxy statements** (`standalone.py`, `insights.py`, `legacy.py`) -- keyed by the policy class's `NAME` attribute (e.g., `NamespaceViewSet`, `CollectionViewSet`).
2. **Pulp viewset overrides** (`pulp.py`) -- keyed by URL pattern (e.g., `repositories/ansible/ansible`). These override the upstream pulp_ansible/pulp_container defaults.
3. **Upstream defaults** -- if no Galaxy or Pulp override exists, `AccessPolicyBase.get_access_policy` loads the viewset's own `DEFAULT_ACCESS_POLICY`. As a last resort, it falls back to admin-only.

Statements are deployment-mode-specific. The `insights` mode wraps every `allow` statement with a `has_rh_entitlements` condition via `_entitelify()`.

### Writing New Access Policies

- Create a subclass of `AccessPolicyBase` with a unique `NAME`.
- Add the corresponding statement list to both `STANDALONE_STATEMENTS` and, if applicable, `INSIGHTS_STATEMENTS`.
- Custom condition methods belong on the policy subclass, not the base class, unless they are reusable across viewsets.
- Use `has_model_or_obj_perms:` for object-level checks, `has_model_perms:` for model-level only. Always use the full `app_label.codename` format (e.g., `galaxy.change_namespace`).
- **Deny statements and entitlement conditions:** The insights `_entitelify` function skips deny statements when adding the `has_rh_entitlements` condition, so denials remain unconditional with respect to entitlements. Deny statements may have other conditions (e.g., `is_local_resource_management_disabled`). If you want an action universally blocked, use `{"principal": "*", "action": "*", "effect": "deny"}` without any condition.

### Protected Resources

The `is_not_protected_base_path` condition prevents deletion of default distributions/repositories with base paths: `rh-certified`, `validated`, `community`, `published`, `staging`, `rejected`. When adding new default distributions, update `PROTECTED_BASE_PATHS` in `access_policy.py`.

## RBAC Systems

Galaxy NG has **two coexisting RBAC systems**:

1. **Legacy Pulp RBAC** (v1/v3/UI v1 endpoints): Uses `pulpcore.plugin.util.assign_role`/`remove_role`, `GroupModelPermissionsMixin`, `UserModelPermissionsMixin` on models, and `GroupPermissionField`/`UserPermissionField` on serializers. Roles are defined in `statements/roles.py` as `LOCKED_ROLES`.

2. **DAB RBAC** (UI v2 endpoints): Uses `ansible_base.rbac.api.permissions.AnsibleBaseObjectPermissions` and `permission_registry.is_registered()` for queryset scoping. Models must be registered in `ANSIBLE_BASE_RBAC_MODEL_REGISTRY` in `settings.py`.

When adding a new model:
- Register it in `ANSIBLE_BASE_RBAC_MODEL_REGISTRY` with the correct `parent_field_name`.
- If the model needs legacy RBAC, add `GroupModelPermissionsMixin` and `UserModelPermissionsMixin`.
- UI v2 viewsets should inherit from `BaseViewSet` (which applies `AnsibleBaseObjectPermissions` and `IsSuperUserOrReadOnly`) and call `cls.access_qs(self.request.user, queryset=qs)` for queryset filtering.

### Resource Server Mode

When `RESOURCE_SERVER__URL` is set (AAP deployment), `IS_CONNECTED_TO_RESOURCE_SERVER` becomes `True`. This:
- Forces JWT-only authentication (`HubJWTAuth`), overriding all other auth classes.
- Disables local user/group/team CRUD (the `is_local_resource_management_disabled` condition blocks create/update/delete).
- Restricts user modification to only the `is_superuser` field via `ComplexUserPermissions`.
- The `ALLOW_LOCAL_ASSIGNING_JWT_ROLES` is set to `False` to prevent local assignment of JWT-synced roles.

## Authentication

### Authentication Class Ordering

Authentication classes are configured via `GALAXY_AUTHENTICATION_CLASSES` and propagated to `REST_FRAMEWORK__DEFAULT_AUTHENTICATION_CLASSES`. The `configure_authentication_classes` hook in `dynaconf_hooks.py` enforces that `galaxy_ng.app.auth.session.SessionAuthentication` is always first. This custom session backend overrides `authenticate_header` to return `"Session"` so DRF returns 401 instead of 403 for unauthenticated requests.

### Backend Presets

Use `AUTHENTICATION_BACKEND_PRESET` (`local`, `ldap`, `keycloak`, `custom`) rather than directly setting `AUTHENTICATION_BACKENDS`. Preset definitions live in `AUTHENTICATION_BACKEND_PRESETS_DATA` in `settings.py`. The `configure_authentication_backends` hook merges preset backends with defaults and always appends `PrefixedUserAuthBackend` for AAP-migrated users.

### Token Expiration

`ExpiringTokenAuthentication` only enforces expiration for Keycloak social-auth users (checked via `token.user.social_auth.get(provider="keycloak")`). Non-social-auth tokens do not expire. The expiration window is `GALAXY_TOKEN_EXPIRATION` (minutes).

### RH Identity Authentication

The `RHIdentityAuthentication` backend decodes a base64 `X-RH-Identity` header. It supports both `User` and `ServiceAccount` identity types. Service account usernames have the `service-account-` prefix stripped for length. The decoded identity is returned as `request.auth['rh_identity']` and used by `has_rh_entitlements` to check entitlement claims.

## Input Validation Patterns

### Namespace Names

The `NamespaceSerializer.validate_name` enforces: lowercase alphanumeric plus underscores only (`^[a-z0-9_]+$`), minimum 3 characters, cannot start with underscore.

### Password Handling

- Passwords use Django's `AUTH_PASSWORD_VALIDATORS` (similarity, minimum length, common, numeric). Minimum length defaults to 9, overridable via `GALAXY_MINIMUM_PASSWORD_LENGTH`.
- Passwords must be declared `write_only=True` in serializer `extra_kwargs`.
- Always use `instance.set_password()`, never assign raw passwords.
- In the v1 UI serializer, only superusers can change another user's password. The v2 serializer delegates this to `ComplexUserPermissions`.

### Superuser Escalation Prevention

- `validate_is_superuser` in the v1 `UserSerializer` blocks non-superusers from granting or revoking superuser status.
- The v1 `UserSerializer.update` blocks non-superusers from modifying superuser accounts entirely.
- `ComplexUserPermissions` (v2) prevents the last superuser from being demoted.
- Access policy statements deny deleting superusers and deny users deleting themselves.

### Sensitive Fields in Serializers

Remote/sync serializers (`CollectionRemoteSerializer`) mark `password`, `token`, `proxy_password`, and `client_key` as `write_only=True`. The `get_write_only_fields` helper in `api/utils.py` reports which write-only fields have values set without exposing the values.

## Security-Related Settings

### Cookie and Header Security

Defaults in `settings.py` (do not weaken without justification):
- `SESSION_COOKIE_SECURE = True`, `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = "Lax"`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `SECURE_HSTS_SECONDS = 63072000` with `INCLUDE_SUBDOMAINS` and `PRELOAD`
- `X_FRAME_OPTIONS = "SAMEORIGIN"`
- `SECURE_REFERRER_POLICY = "same-origin"`

### Unauthenticated Access

Both `GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS` and `GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD` default to `False`. These are checked as access policy conditions (`unauthenticated_collection_access_enabled`, `unauthenticated_collection_download_enabled`) and must remain paired in statements: anonymous access requires both the feature flag condition and any applicable repo-visibility checks.

### Keycloak SSL Verification

`GALAXY_VERIFY_KEYCLOAK_SSL_CERTS` defaults to `False`. In production, set this to `True` or a CA bundle path.

### API Access Logging

When `GALAXY_ENABLE_API_ACCESS_LOG` is enabled, the `AUTOMATED_LOGGING` config masks these fields in request data: `ca_cert`, `client_cert`, `client_key`, `email`, `password`, `proxy_url`, `proxy_username`, `proxy_password`, `token`, `username`. When adding new endpoints that accept credentials, add the field names to this mask list in `dynaconf_hooks.py`.

### Dynamic Settings

Only keys listed in `DYNAMIC_SETTINGS_SCHEMA` (`galaxy_ng/app/dynamic_settings.py`) can be overridden from the database. Never add authentication or authorization settings to this schema.

### Settings Exposed to UI

The `SettingsView` (`_ui/v1/views/settings.py`) exposes a curated allowlist of setting keys. Never add secrets (`SECRET_KEY`, passwords, tokens, private keys) to this list.

## Community Sync Safety

The `require_requirements_yaml` condition and `CollectionRemoteSerializer.validate` both enforce that syncing from community domains (`galaxy.ansible.com`, `beta-galaxy.ansible.com`) requires a `requirements_file`. This prevents accidentally mirroring the entire community Galaxy.

## Hostname Settings and Request Headers

The `alter_hostname_settings` hook dynamically sets `CONTENT_ORIGIN`, `ANSIBLE_API_HOSTNAME`, and `TOKEN_SERVER` from request headers (`X-Forwarded-Proto`, `X-Forwarded-Host`, or RFC 7239 `Forwarded`). When connected to a resource server, these headers are mandatory for content downloads -- missing headers raise `SuspiciousOperation` (400). This is intentional to prevent content URL manipulation when behind a gateway.
