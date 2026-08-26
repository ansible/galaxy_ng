# Error Handling Guidelines

## Custom Exception Handler

Galaxy NG uses a custom DRF exception handler registered in settings as `GALAXY_EXCEPTION_HANDLER` (see `galaxy_ng/app/api/exceptions.py`). All views that inherit from `galaxy_ng.app.api.base` (APIView, ViewSet, ModelViewSet, etc.) use it via `LocalSettingsMixin.get_exception_handler()`.

The handler normalizes all `APIException` subclasses into this response format:

```json
{
  "errors": [
    {
      "status": "400",
      "code": "invalid",
      "title": "Invalid input.",
      "detail": "This field is required.",
      "source": {"parameter": "name"}
    }
  ]
}
```

Key behaviors:
- `status` is always a string, not an integer.
- `title` comes from the exception class's `default_detail`, not the instance detail.
- `detail` is omitted when it equals `title` (to avoid redundancy).
- `source.parameter` is omitted for non-field errors (i.e., `non_field_errors`).
- Django's `Http404` and `PermissionDenied` are converted to their DRF equivalents before formatting.
- Non-`APIException` exceptions return `None`, falling through to Django's default 500 handling.

## Which ValidationError to Use

There are two `ValidationError` classes in play. Use the correct one depending on context.

| Context | Import | Why |
|---------|--------|-----|
| Serializers, viewsets, views (API layer) | `from rest_framework.exceptions import ValidationError` | Handled by the custom exception handler; produces the `{"errors": [...]}` format. |
| Model `clean()` / `full_clean()` | `from django.core.exceptions import ValidationError` | Required by Django's validation protocol. |

**Do not** use Django's `ValidationError` in API views or serializers. It is not an `APIException` subclass, so the custom handler returns `None` and Django emits an unformatted 500 error.

When a file needs both (rare), alias one explicitly:

```python
from django.core.exceptions import ValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError
```

## Custom Exception Classes

### ConflictError (`galaxy_ng/app/exceptions.py`)

```python
from galaxy_ng.app.exceptions import ConflictError
```

- Subclass of DRF `ValidationError` with `status_code = 409`.
- Use for duplicate-resource creation (e.g., namespace name already exists).
- Pass `detail` as a dict keyed by field name: `raise ConflictError(detail={'name': _('...')})`.

### CouldNotCreateContainerError (`galaxy_ng/app/tasks/index_registry.py`)

- Plain `Exception` subclass, not an `APIException`.
- Used only inside Pulp tasks (not API views). Pulp catches the exception and marks the task as failed.
- Accepts `remote_name` and optional `error` string.

## Raising Validation Errors in Serializers

### Field-level validation (`validate_<field>`)

Return the validated value on success. On failure, raise `ValidationError` with a `detail` dict keyed by the field name:

```python
def validate_name(self, name):
    if len(name) <= 2:
        raise ValidationError(detail={
            'name': _('Name must be longer than 2 characters')
        })
    return name
```

This convention is consistent across `NamespaceSerializer`, `UserSerializer`, `UserCreateUpdateDeleteSerializer`, and `ContainerRemoteSerializer`.

### Object-level validation (`validate`)

Raise `serializers.ValidationError` with a `detail` dict:

```python
def validate(self, data):
    if bad_condition:
        raise serializers.ValidationError(
            detail={'requirements_file': _('...')}
        )
    return super().validate(data)
```

### ScopedErrorListSerializer pattern

When a parent serializer contains a list of child serializers that share field names with the parent, use `ScopedErrorListSerializer` (defined in `galaxy_ng/app/api/v3/serializers/namespace.py`). It prefixes child error keys with `<scoped_error_name>__<field>` to disambiguate:

```python
class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        list_serializer_class = ScopedErrorListSerializer
        scoped_error_name = 'links'
```

## Raising Errors in Views

### Prefer exceptions over manual Response objects

Raise DRF exceptions rather than constructing `Response(data, status=4xx)`. The exception handler ensures consistent error formatting.

```python
# Correct
raise ValidationError(detail={'remote': _('No remote associated.')})

# Avoid (bypasses error formatting)
return Response({"detail": "..."}, status=status.HTTP_400_BAD_REQUEST)
```

### NotFound for missing resources

Use `rest_framework.exceptions.NotFound` when a resource lookup fails in a view:

```python
except ObjectDoesNotExist:
    raise NotFound(_('Collection %s not found') % self.version_str)
```

### HttpResponseBadRequest for gateway redirects

`HttpResponseBadRequest` is used only in `_ui/v2/` views to tell clients to use the gateway API instead. This is a deliberate pattern for resource-server mode -- do not use it for general validation errors.

## Error Handling in Pulp Tasks

Tasks run asynchronously via `pulpcore.plugin.tasking.dispatch`. Unhandled exceptions cause Pulp to mark the task as failed and store the traceback.

### Use RuntimeError for infrastructure failures

When a required resource (repository, signing service) is missing at task execution time, raise `RuntimeError`:

```python
raise RuntimeError(_('Could not find staging repository: "%s"') % STAGING_NAME)
raise RuntimeError(f'Signing {SIGNING_SERVICE_NAME} service not found')
```

### Use ValidationError for data validation in tasks

DRF's `ValidationError` is used in tasks like `_download_avatar` for data-level problems (oversized file, invalid image). Pulp records it as a task failure.

### Subtask isolation

When processing a list of items, dispatch each as a subtask so one failure does not block the rest. See `index_execution_environments_from_redhat_registry` which dispatches `create_or_update_remote_container` per remote.

## Logging Patterns

### Logger naming

Use module-level loggers:

```python
log = logging.getLogger(__name__)
```

Exception: the legacy role import task uses a descriptive name:
```python
logger = logging.getLogger("galaxy_ng.app.api.v1.tasks.legacy_role_import")
```

### When to log errors

- `log.exception(exc)` -- for caught exceptions where the traceback is needed (e.g., auth failures in `galaxy_ng/app/auth/auth.py`).
- `log.exception('Failed to publish artifact ...')` -- when re-raising after logging context (e.g., `CollectionUploadViewSet.create`).
- `log.error(...)` -- for non-exception error conditions (e.g., unexpected data shapes in management commands).
- `log.warning(...)` -- for degraded but non-fatal conditions (e.g., unparseable filenames, malformed multipart bodies).

### Structured access logging

Upload events use a dedicated logger for audit trails:

```python
api_access_log = logging.getLogger("automated_logging")
api_access_log.info("Collection uploaded by user '%s': %s-%s-%s", username, namespace, name, version)
```

## Internationalization

Wrap user-facing error messages in `gettext_lazy`:

```python
from django.utils.translation import gettext_lazy as _

raise ValidationError(detail={'name': _('Name must be longer than 2 characters')})
```

This is consistently used across v3 serializers, sync views, signing views, and EE serializers. New code should always use `_()`.

## Summary of Exception Types by Layer

| Layer | Exception | Effect |
|-------|-----------|--------|
| API views/serializers | `rest_framework.exceptions.ValidationError` | 400 with `{"errors": [...]}` |
| API views | `rest_framework.exceptions.NotFound` | 404 with `{"errors": [...]}` |
| API views | `rest_framework.exceptions.PermissionDenied` | 403 with `{"errors": [...]}` |
| API views | `rest_framework.exceptions.APIException` | 500 with `{"errors": [...]}` |
| API views | `galaxy_ng.app.exceptions.ConflictError` | 409 with `{"errors": [...]}` |
| Pulp tasks | `RuntimeError` | Task marked failed |
| Pulp tasks | `CouldNotCreateContainerError` | Task marked failed |
| Pulp tasks | `ValidationError` (DRF) | Task marked failed |
| Models | `django.core.exceptions.ValidationError` | Used by `full_clean()` |
