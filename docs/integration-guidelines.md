# Integration Guidelines

Rules and conventions for Pulp tasks, signal handlers, external service integrations,
and async patterns in galaxy_ng.

## Pulp Task Dispatch

All async work runs through Pulp's tasking system, not raw Celery.

1. **Always use `pulpcore.plugin.tasking.dispatch`** to create async tasks. Never use
   Celery's `apply_async` or `delay` directly. The `dispatch` function handles resource
   locking, task tracking, and worker routing.

2. **Task functions must be top-level module functions** (not methods). They are
   resolved by import path at execution time. All arguments must be serializable --
   pass primary keys, not model instances.

3. **Resource locking uses two tiers:**
   - `exclusive_resources`: The task has sole access to these resources. Other tasks
     requesting the same resource will queue. Pass model instances or querysets.
   - `shared_resources`: Multiple tasks can hold shared locks simultaneously, but
     they block exclusive locks. Used when a task only reads from a resource.

4. **Lock model instances, not arbitrary strings.** The one exception in the codebase
   is `exclusive_resources=["/api/v3/distributions/"]` in `index_registry.py`, which
   uses a URI string as a global mutex for distribution creation. Prefer model
   instances for all other cases.

5. **Lock ordering matters.** When locking multiple resources (e.g., source and
   destination repos), include all of them in a single `dispatch` call. Do not acquire
   locks incrementally across multiple dispatches -- this risks deadlocks.

## Task Composition Patterns

6. **Chain tasks by dispatching from within a running task.** Galaxy NG does not use
   Celery chains or chords. Instead, a parent task calls `dispatch()` for subtasks.
   See `publishing.py`: `import_to_staging` runs the upload, then dispatches
   `add_and_remove` as a follow-up with an exclusive lock on the repo.

7. **Use `TaskGroup` for logically grouped operations.** Create a `TaskGroup` before
   dispatching related subtasks, pass it via `task_group=task_group`, and call
   `task_group.finish()` after the last dispatch. See `promotion.py:call_auto_approve_task`.

8. **Access the current task via `Task.current()`**, never by threading or global state.
   Use `current_task.created_resources` to discover objects created by upstream pipeline
   steps (e.g., finding `CollectionVersion` objects after `general_create` runs).

9. **Wrap multi-step sequences in a single dispatched function** when they must share
   the same lock. See `signing.py:sign_and_move` -- signing and moving run in one task
   function to hold exclusive locks on both repos for the entire duration.

## Sync Task Patterns

10. **Collection sync** delegates to `pulp_ansible.app.tasks.collections.sync`. The
    viewset validates the remote/distribution relationship, then dispatches with
    exclusive locks on both the repository and the remote.

11. **Container sync** delegates to `pulp_container.app.tasks.synchronize.synchronize`.
    The `launch_container_remote_sync` helper copies registry connection fields onto
    the remote before dispatching. The remote gets a shared lock; the repository gets
    an exclusive lock.

12. **Registry-wide sync** (`sync_all_repos_in_registry`) iterates all repos in a
    registry and dispatches individual container syncs. Each sync is an independent
    task with its own locks -- they can run in parallel.

13. **Red Hat Catalog indexing** (`index_execution_environments_from_redhat_registry`)
    paginates through the catalog API, then dispatches one subtask per container with
    a global distribution lock. Use `registry.get_downloader(url=...)` to make
    authenticated HTTP requests through Pulp's downloader infrastructure.

14. **Legacy role sync** (`legacy_sync_from_upstream`) runs synchronously within a
    single Pulp task -- it does not dispatch subtasks. It iterates an upstream v1 API
    using `upstream_role_iterator` and upserts `LegacyRole` records directly.

15. **DAB resource sync** (`resource_sync.run`) is a periodic task that syncs
    users/teams/roles with a resource server. It short-circuits early if
    `RESOURCE_SERVER` is not configured.

## Signal Handler Conventions

16. **Signals are registered in `galaxy_ng/app/signals/handlers.py`** and imported in
    `PulpGalaxyPluginAppConfig.ready()`. Never import signal handlers at module top
    level elsewhere.

17. **Cross-model consistency signals** automatically create Galaxy objects when Pulp
    objects are saved:
    - `Collection` post_save -> creates `Namespace` if missing
    - `AnsibleNamespaceMetadata` post_save -> updates Galaxy `Namespace` fields
    - `AnsibleRepository` post_save -> sets `retain_repo_versions=1`
    - `AnsibleDistribution` post_save -> attaches content guard

18. **RBAC sync signals use re-entrancy guards.** The `rbac_state` thread-local tracks
    whether a signal was triggered by a Pulp RBAC change or a DAB RBAC change. Always
    check `rbac_signal_in_progress()` at the top of every RBAC signal handler to prevent
    infinite loops. Use the `pulp_rbac_signals()` or `dab_rbac_signals()` context
    managers to mark the origin of the change.

19. **Role name mapping** between Pulp and DAB uses the `PULP_TO_ROLEDEF` and
    `ROLEDEF_TO_PULP` dictionaries. When adding new roles that need sync, add entries
    to both maps.

20. **The `m2m_changed` signal** is used for permission sync between `Role.permissions`
    and `RoleDefinition.permissions`. These handlers reject reverse-relationship changes
    by raising `RuntimeError` -- always modify permissions through the forward relation.

## External Service Integration

21. **Red Hat Catalog API** is accessed at `https://catalog.redhat.com/api/containers/v1/repositories`.
    Requests use Pulp's `registry.get_downloader()` which handles auth and TLS. Responses
    are paginated; iterate until `len(data['data']) < data['page_size']`.

22. **Avatar/logo downloads** use `pulpcore.plugin.download.HttpDownloader` with a custom
    aiohttp session. The downloaded file is validated as a PIL image or SVG, capped at
    3MB, and stored as a Pulp `Artifact`.

23. **Settings cache** uses Redis (via `galaxy_ng/app/tasks/settings_cache.py`). The
    `connection_error_wrapper` decorator gracefully degrades when Redis is unavailable.
    Use `acquire_lock`/`release_lock` for distributed locking on settings updates.

## Legacy (v1) Task Conventions

24. **Legacy tasks use `LegacyTasksMixin.legacy_dispatch`** which wraps `dispatch()` and
    converts the Pulp UUID task ID to an integer via `uuid_to_int()` for v1 API
    compatibility.

25. **Legacy role imports capture logs** via `LegacyRoleImportHandler`, a custom
    `logging.Handler` that writes log records into `LegacyRoleImport.messages`. The
    handler discovers the current task via `Task.current()` and attaches records to the
    corresponding import model.

## Task Scheduling

26. **Use the `task-scheduler` management command** to register periodic tasks with
    Pulp's `TaskSchedule` model. It accepts `--id`, `--path` (importable function path),
    `--interval` (minutes), and `--force` to overwrite existing schedules. Do not use
    Celery Beat or Django-celery-beat.

## Metrics

27. **Prometheus counters** are defined in `galaxy_ng/app/common/metrics.py`. Increment
    them in viewset code (not in tasks). Current counters track collection import
    attempts/successes/failures and artifact download attempts/successes/failures.

## Deletion Tasks

28. **Content deletion requires orphan cleanup.** Pulp content is immutable within
    repository versions. To delete content: remove it from the latest repo version
    via `general_multi_delete` or `recursive_remove_content`, then call `orphan_cleanup`
    to delete artifacts. See `deletion.py` for the two-step pattern.

29. **Disk reclamation** uses `pulpcore.app.tasks.reclaim_space` with `keeplist_rv_pks`
    pointing to the latest repo version and `force=True`.

## Response Patterns

30. **Async endpoints return 202.** Use `OperationPostponedResponse(result, request)`
    for standard Pulp task responses, or return `Response({'task': result.pk})` for
    custom response shapes. The v1 API returns an integer task ID in a `results` array
    for backward compatibility.
