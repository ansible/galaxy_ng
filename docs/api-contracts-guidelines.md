# API Contracts Guidelines

Rules for designing, extending, and maintaining the Galaxy NG REST API.

## API Versions: When to Use Each

| Version | Path Prefix | Purpose | Audience |
|---------|-------------|---------|----------|
| **v1** | `/api/{PREFIX}/v1/` | Legacy roles (old Galaxy compatibility) | `ansible-galaxy role` CLI. Feature-gated by `GALAXY_ENABLE_LEGACY_ROLES`. |
| **v3** | `/api/{PREFIX}/v3/` and `/api/{PREFIX}/content/<path>/v3/` | Standard Galaxy API for collections and EE operations | `ansible-galaxy collection` CLI, external automation tools. |
| **UI v1** | `/api/{PREFIX}/_ui/v1/` | UI-optimized endpoints (collections, namespaces, users, groups) | Hub UI frontend. Uses `UIVersioning` (which extends `NamespaceVersioning`). |
| **UI v2** | `/api/{PREFIX}/_ui/v2/` | DAB RBAC-native endpoints (users, groups, orgs, teams) | Hub UI frontend on AAP deployments. Uses DAB pagination and permissions. |

**Rules:**
1. CLI-facing endpoints go in `v3/`. UI-specific data shaping goes in `ui/v1/` or `ui/v2/`.
2. Avoid adding new endpoints to `v1/` -- it exists only for backward compatibility with old Galaxy. Exceptions may be made for critical CLI compatibility (e.g., `removerole` added in 2023).
3. New DAB RBAC-integrated resources go in `ui/v2/`. Legacy permission models stay in `ui/v1/`.
4. Distribution-scoped content endpoints use the `content/<path>/v3/` URL pattern.

## ViewSet Base Classes

All v3 and UI v1 viewsets **must** inherit from `galaxy_ng.app.api.base` classes, not directly from DRF:

| Base Class | Use When |
|-----------|----------|
| `api_base.ModelViewSet` | Full CRUD on a Django model |
| `api_base.GenericViewSet` | Composing specific mixins (`ListModelMixin`, `RetrieveModelMixin`, etc.) |
| `api_base.ViewSet` | Non-model endpoints with custom actions |
| `api_base.APIView` | Single-action views (not routed via a router) |

These base classes provide `LocalSettingsMixin`, which injects the project-wide authentication classes, pagination class (`pulp_ansible LimitOffsetPagination`), exception handler, and a `_MustImplementPermission` guard that forces every viewset to declare `permission_classes`.

**Pulp viewset extension pattern:** When extending a Pulp viewset (e.g., `pulp_core_viewsets.TaskViewSet`), inherit from `LocalSettingsMixin` plus the Pulp viewset to get Galaxy's settings without double-inheriting from DRF base classes. See `TaskViewSet` for this pattern.

**UI v2 exception:** UI v2 viewsets inherit from a local `BaseViewSet(viewsets.ModelViewSet)` that uses DAB's `DefaultPaginator` and `AnsibleBaseObjectPermissions`. Do **not** mix `api_base` classes with UI v2 views.

**v1 exception:** Legacy viewsets use bare DRF `viewsets.ModelViewSet` with `PageNumberPagination` and manual `GALAXY_AUTHENTICATION_CLASSES` assignment, matching old Galaxy API behavior. Do not refactor these to use `api_base`.

## Pagination

| API Version | Pagination Style | Query Parameters |
|------------|-----------------|------------------|
| v3, UI v1 | `LimitOffsetPagination` (from pulp_ansible) | `?limit=N&offset=M` |
| UI v2 | DAB `DefaultPaginator` | `?page=N&page_size=M` |
| v1 | `PageNumberPagination` | `?page=N&page_size=M` (max 1000) |

Never override pagination_class without a documented reason. When composing a viewset from `GenericViewSet` + mixins, call `self.paginate_queryset()` and `self.get_paginated_response()` -- do not return bare lists.

## Serializer Conventions

1. **UI v1 serializers** inherit from the project's `galaxy_ng.app.api.ui.v1.serializers.base.Serializer`, which auto-generates `Meta.ref_name` as `galaxy.<ClassName>` (stripping the "Serializer" suffix) for OpenAPI spec deduplication.

2. **v3 serializers** use `pulpcore.plugin.serializers.ModelSerializer` (aliased as `PulpModelSerializer`) for Pulp models, or plain DRF `serializers.ModelSerializer` for non-Pulp models.

3. **UI v2 serializers** use plain DRF `serializers.ModelSerializer`.

4. **List vs. Detail serializers:** Viewsets that need different field sets for list and detail **must** implement `get_serializer_class()` returning a Summary/List serializer for `self.action == 'list'` and a full serializer otherwise. Follow the existing pattern in `NamespaceViewSet`, `TaskViewSet`, `CollectionViewSet`, and `CollectionImportViewSet`.

5. **Pulp timestamp fields:** Remap `pulp_created` to `created_at` and `pulp_last_updated` to `updated_at` via `serializers.DateTimeField(source='pulp_created')`. This is the project convention; do not expose `pulp_*` names in responses.

6. **Sensitive fields:** Mark passwords and tokens as `write_only=True` and `style={'input_type': 'password'}`. Expose `write_only_fields` as a serializer method field using `galaxy_ng.app.api.utils.get_write_only_fields()` so the client knows which write-only fields have values set.

7. **`RelatedFieldsBaseSerializer`:** Use this (from `api.base`) for optional expensive related data. Fields are only returned when the client passes `?include_related=<field_name>`.

8. **`ref_name` on Meta:** When two serializers wrap the same model, set `ref_name` explicitly to avoid OpenAPI spec collisions (e.g., `ref_name = "Task"`).

## URL Routing Patterns

1. **v3 and UI v1** use DRF `SimpleRouter`. **UI v2** uses `DefaultRouter` (which adds an API root view).

2. **Name convention:** `<resource>-list`, `<resource>-detail` for standard CRUD. Nested resources use `<parent>-<child>-list` (e.g., `container-repository-images`).

3. **Viewset-to-URL wiring for non-router endpoints** uses explicit `path()` calls with `.as_view({'get': 'list', 'post': 'create'})` action maps. Always include trailing slashes.

4. **v1 duplicates routes with and without trailing slashes** for old Galaxy CLI compatibility. This pattern must not be replicated in other API versions.

5. **Feature-gated paths:** Conditional URL inclusion uses `settings.GALAXY_FEATURE_FLAGS`. Check the flag before appending to `urlpatterns`:
   ```python
   if settings.GALAXY_FEATURE_FLAGS['execution_environments']:
       paths.append(path('execution-environments/', include(container_paths)))
   ```

6. **Nested container paths** use `_content/` as a namespace separator to avoid conflicts with user-named resources (e.g., `repositories/<base_path>/_content/images/`).

## Access Control

1. Every v3 and UI v1 viewset **must** set `permission_classes` to a subclass of `AccessPolicyBase`. The base class raises `NotImplementedError` if omitted. UI v2 and v1 viewsets follow the version-specific exceptions documented below.

2. Access policy classes live in `galaxy_ng.app.access_control.access_policy`. Name them `<Resource>AccessPolicy`.

3. UI v2 uses DAB's `AnsibleBaseObjectPermissions` plus a project-specific `IsSuperUserOrReadOnly`. These viewsets also apply RBAC queryset filtering in `filter_queryset()` via `cls.access_qs(request.user)`.

## Error Response Format

The custom exception handler (`galaxy_ng.app.api.exceptions.exception_handler`) returns errors in this structure:

```json
{
  "errors": [
    {
      "status": "400",
      "code": "invalid",
      "title": "Invalid input.",
      "detail": "Name must be longer than 2 characters",
      "source": {"parameter": "name"}
    }
  ]
}
```

- Use DRF's `ValidationError` and `NotFound` -- the handler converts them automatically.
- Use `galaxy_ng.app.exceptions.ConflictError` (HTTP 409) for duplicate resource creation.
- For async operations, return `{"task": "<task_href>"}` with HTTP 202.

## Filtering and Ordering

1. Use `django_filters.rest_framework.DjangoFilterBackend` as the filter backend. Declare `filter_backends = (DjangoFilterBackend,)` and `filterset_class`.

2. Ordering uses `django_filters OrderingFilter` declared as a `sort` field on the filterset (not DRF's `OrderingFilter`). The query parameter is `?sort=name` or `?sort=-name`.

3. Keyword/search filters are implemented as custom `CharFilter(method='...')` methods on the filterset.

4. v1 filtering uses `DjangoFilterBackend` with a separate `LegacyRoleFilter` filterset -- same pattern, different models.

## Backward Compatibility

1. **Pulp endpoint overrides:** When Galaxy NG must override a pulp_ansible endpoint, place it **above** the `include(v3_urls)` line in `v3/urls.py` and add a comment explaining why.

2. **Disabled endpoints:** Use `views.NotFoundView` to explicitly disable inherited endpoints that should not be exposed (e.g., unpaginated `collections/all/`).

3. **Redirect views:** Use `ApiRedirectView` for legacy URL compatibility (`/api/` suffix appended by older `ansible-galaxy` clients).

4. **UI v1 viewsets reuse v3 viewsets** by subclassing and adding `versioning_class = versioning.UIVersioning`. This keeps business logic in one place. Follow this pattern for new resources that need both v3 and UI representations.

5. **Never remove or rename a field** in v3 or UI v1 responses without a deprecation period. Add new fields alongside old ones, then remove old fields in a future major version.

## Async Operations

For long-running operations (imports, syncs, moves, copies):
1. Dispatch via `pulpcore.plugin.tasking.dispatch()`.
2. Return HTTP 202 with a `task` href pointing to the tasks detail endpoint.
3. Create a `CollectionImport` or equivalent tracking model linking the Pulp task to Galaxy metadata.

## OpenAPI / Swagger

1. Use `@extend_schema` from `drf_spectacular` for non-obvious endpoints. At minimum, document custom `responses` and `request` bodies.
2. Use `@extend_schema_field` on `SerializerMethodField` declarations so the generated schema has correct types.
3. Guard `get_queryset()` with `if getattr(self, 'swagger_fake_view', False): return Model.objects.none()` when the queryset depends on request kwargs.
