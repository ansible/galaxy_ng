# Performance Guidelines

Rules and conventions for writing performance-aware code in galaxy_ng.

## Pulp Task Dispatch and Resource Locking

Galaxy NG runs async work through Pulp's `dispatch()` from `pulpcore.plugin.tasking`. When a task accesses repositories or other shared resources that require locking, declare which resources it needs and whether access is exclusive or shared.

### Exclusive vs shared resources

- **`exclusive_resources`** grants sole access. Use for any operation that mutates a repository (adding/removing content, creating new repository versions).
- **`shared_resources`** allows concurrent readers. Use when the task only reads from a resource.
- When a task touches multiple repositories, list all of them. The signing task locks both source and dest repos exclusively to prevent interleaving:
  ```python
  dispatch(sign_and_move, exclusive_resources=[source_repo, dest_repo], ...)
  ```
- The promotion task uses a split lock pattern -- exclusive on the destination repos, shared on the source:
  ```python
  dispatch(move_collection, exclusive_resources=published_repos, shared_resources=[source_repo], ...)
  ```

### Upload concurrency pattern

Collection uploads deliberately pop `repository_pk` before calling `general_create()` so the import task does not hold a repository lock while processing the tarball. A separate `dispatch()` with `exclusive_resources=[repo]` adds content to the repo afterward. Follow this pattern for any long-running import that ends with a repo mutation -- separate the compute from the lock.

### String-based resource locks

The codebase has one exceptional case where a URL path string is used as an exclusive resource for global serialization:
```python
dispatch(..., exclusive_resources=["/api/v3/distributions/"])
```
This serializes all subtasks that operate on distributions without locking a specific model object. This pattern exists only in `index_registry.py`. Prefer locking model instances for all other cases.

### TaskGroup usage

Use `TaskGroup` when dispatching related subtasks from within a parent task. Call `task_group.finish()` after dispatching all children (see `call_auto_approve_task`). For top-level API endpoints, create the group before dispatch:
```python
task_group = TaskGroup.objects.create(description="...")
dispatch(my_task, kwargs=kwargs, task_group=task_group)
```

## Database Query Optimization

### select_related and prefetch_related

Use `select_related` for ForeignKey/OneToOne joins that will be accessed in serialization:
```python
queryset = ContainerDistribution.objects.all().select_related('namespace')
```

Use `prefetch_related` with explicit `Prefetch` objects to scope related querysets, especially when content must be filtered to a specific repository version:
```python
Prefetch('tagged_manifests', container_models.Tag.objects.filter(pk__in=repo_content))
```
Without scoping, prefetches can pull tags/manifests from all repository versions, causing thousands of unnecessary rows.

The `CollectionImportViewSet` shows the pattern for list views with related models:
```python
queryset = PulpCollectionImport.objects.prefetch_related("task", "galaxy_import").all()
```

### values_list for scalar queries

When you only need PKs or a single column, use `values_list("pk", flat=True)` instead of fetching full model instances. This is used throughout the task layer (e.g., `promotion.py` fetching repo PKs).

### .only() for partial model loading

When serializing a subset of fields from a large model, use `.only()`:
```python
CollectionVersion.objects.filter(...).only("content_ptr_id", "version")
```

### Annotation-based filtering over Python filtering

The collection list view uses database annotations (`Func`, `Exists`, `Case/When`) to compute `deprecated`, `sign_state`, and `version_identifier` at the SQL level rather than in Python. Follow this pattern for any computed field that is filterable.

## Search and Full-Text

- `LegacyRoleSearchVector` maintains a `SearchVectorField` with a `GinIndex`, updated by a PostgreSQL trigger on `LegacyRole` save. The unified search view (`SearchListView`) queries this alongside pulp_ansible's `search_vector` on `CollectionVersion`.
- Use `ts_rank` with normalization (`RANK_NORMALIZATION = 32`) for relevance scoring.
- The search view builds separate annotated querysets for collections and roles, then combines them with `UNION ALL`. Filters are applied to each branch individually before the union.

## Pagination

- **v3/UI endpoints**: Use `pulp_ansible.app.galaxy.v3.pagination.LimitOffsetPagination` (set via `GALAXY_PAGINATION_CLASS`). This is limit/offset based.
- **v1 legacy endpoints**: Use DRF's `PageNumberPagination` with explicit bounds:
  ```python
  page_size = 10
  page_size_query_param = 'page_size'
  max_page_size = 1000
  ```
- **UI v2 endpoints**: Use `ansible_base.rest_pagination.default_paginator.DefaultPaginator`.
- Always set bounds on custom paginators to prevent clients from requesting unbounded result sets: use `max_limit` for `LimitOffsetPagination` subclasses (v3/UI) and `max_page_size` for `PageNumberPagination` subclasses (v1 legacy).

## RelatedFieldsBaseSerializer (Lazy Related Data)

The `RelatedFieldsBaseSerializer` base class in `galaxy_ng/app/api/base.py` enables opt-in related data via `?include_related=field_name`. Fields in this serializer are only evaluated when the client requests them, reducing default query cost. Use this pattern for any related data that requires additional queries (e.g., `my_permissions`).

## Redis Settings Cache

Dynamic settings use a Redis-backed cache (`galaxy_ng/app/tasks/settings_cache.py`):

- **Connection**: Lazily initialized singleton from `REDIS_HOST`/`REDIS_URL` settings. Falls back gracefully when Redis is unavailable.
- **Cache key**: `GALAXY_SETTINGS_DATA` stored as a Redis hashmap. TTL defaults to 24 hours (`GALAXY_SETTINGS_EXPIRE`).
- **Locking**: The `SettingsManager.create()` method uses Redis `SET NX EX` for distributed locking with a 20-second timeout and 10 retry attempts. Always use `acquire_lock`/`release_lock` for settings mutations.
- **Cache invalidation**: Triggered automatically via django-lifecycle hooks (`AFTER_CREATE`, `AFTER_DELETE` with `on_commit=True`). The entire hashmap is replaced on each write.

## Transaction Management

### @transaction.atomic on view methods

Wrap create/destroy view methods that perform multiple related writes:
```python
@transaction.atomic
def create(self, request, *args, **kwargs):
    ...
```
The `NamespaceViewSet.create()` and `destroy()` both use this to ensure consistency between namespace and related objects.

### select_for_update for counters

The download counter uses `select_for_update()` inside `transaction.atomic` to prevent lost updates from concurrent requests:
```python
with transaction.atomic():
    counter = LegacyRoleDownloadCount.objects.select_for_update().get(pk=counter.pk)
    counter.count += 1
    counter.save()
```
Wrap the entire get-or-create + lock + increment sequence in one atomic block. Catch `DatabaseInternalError` for read-only database failover scenarios.

### Scoped atomic blocks in bulk operations

The legacy sync task wraps individual role saves in `transaction.atomic()` so that a failure on one role does not roll back the entire sync:
```python
for role_data in upstream_roles:
    with transaction.atomic():
        role.full_metadata = new_metadata
        role.save()
```

## Deletion and Disk Reclamation

Deleting content follows a multi-step pattern:
1. `general_multi_delete` removes the distribution/repository objects.
2. `orphan_cleanup` removes content objects no longer in any repository version.
3. `reclaim_space` reclaims disk for artifacts no longer referenced.

Always pass `orphan_protection_time=0` when cleaning up after an intentional delete. Use `keeplist_rv_pks` with `reclaim_space` to preserve the latest repository version's artifacts.

## Concurrency Considerations

- **Upload tasks** should never hold a repository lock during long-running import/validation. Separate compute from repository mutation.
- **Sync tasks** use `shared_resources=[remote]` and `exclusive_resources=[repository]` so multiple syncs can read the same remote config concurrently but each repository is synced serially.
- **Index registry tasks** dispatch per-container subtasks with a common string lock (`/api/v3/distributions/`) so container creation is serialized but the parent task doesn't block.
- **Settings mutations** use Redis-based distributed locks, not database locks, to avoid holding DB connections during cache updates.
