# Database Guidelines

Conventions for working with Django models, migrations, and database patterns in galaxy_ng.

## App Label

Galaxy NG uses the app label `"galaxy"`. All models live under `galaxy_ng.app` but Django
references them as `galaxy.ModelName`. In migrations, use `apps.get_model("galaxy", "Namespace")`.

## Model Inheritance Patterns

Galaxy NG models relate to upstream Pulp/DAB models in three distinct ways:

### Proxy Models (no new table)
Use proxy models to add Galaxy-specific behavior to Pulp or container models without creating
a new database table. Set `default_related_name = "%(app_label)s_%(model_name)s"` to
avoid reverse accessor clashes. Example: `ContainerDistribution`, `ContainerNamespace`.

```python
class ContainerDistribution(container_models.ContainerDistribution, LifecycleModelMixin, ...):
    class Meta:
        proxy = True
        default_related_name = "%(app_label)s_%(model_name)s"
```

Note: The `Group` proxy model is an exception that does not set `default_related_name`.

### Concrete extension via inheritance (new table, shared PK)
`ContainerRegistryRemote` inherits from `pulp_models.Remote`, creating a new table that shares
the Pulp UUID primary key. Use this when you need Galaxy-specific columns on a Pulp base type.

### FK/OneToOne to Pulp models (separate table)
`CollectionImport` links to `PulpCollectionImport` via a `OneToOneField` used as `primary_key`.
`Namespace` has a nullable FK to `AnsibleNamespaceMetadata`. This is the most common pattern
for Galaxy-only models that reference Pulp content.

## Legacy v1 Models Are Outside `app/models/`

Legacy role models (`LegacyNamespace`, `LegacyRole`, `LegacyRoleTag`, etc.) live in
`galaxy_ng/app/api/v1/models.py`, not in `galaxy_ng/app/models/`. They are still under the
`"galaxy"` app label and use standard Django migrations. They use plain `models.Model`
(no LifecycleModel) and `JSONField` for flexible metadata storage instead of many columns.

## LifecycleModel Conventions

All core Galaxy models (Namespace, SyncList, CollectionImport, NamespaceLink) inherit from
`django_lifecycle.LifecycleModel`. When extending a Pulp base class (proxy or concrete), use
`LifecycleModelMixin` as a mixin instead, because `LifecycleModel` itself inherits from
`models.Model` and would cause MRO conflicts.

### Hook Patterns

- **`on_commit=True`**: Use for side effects that should only fire after the transaction commits
  (e.g., cache invalidation). See `Setting._hook_update_create`.
- **`BEFORE_CREATE`**: Use for validation or creating dependent objects before save. See
  `Team._create_related_group` which creates the backing `Group` before the `Team` is saved.
- **`AFTER_UPDATE` with `has_changed()`**: Use to propagate name changes to related objects.
  See `Organization._after_update` and `Team._rename_related_group`.
- **`BEFORE_DELETE` / `AFTER_DELETE`**: Use to cascade custom cleanup. See `Organization` and
  `Team` delete hooks for managing the Group<->Team relationship.
- **`after_save` (string form)**: Used in access-control mixins to defer permission assignment
  until after the object has a PK. See `GroupModelPermissionsMixin.set_object_groups`.

## Django Signals

Signal handlers live in `galaxy_ng/app/signals/handlers.py` and are imported in
`PulpGalaxyPluginAppConfig.ready()`. Signals are used to react to saves on **upstream Pulp
models** that Galaxy cannot subclass (e.g., `AnsibleRepository`, `Collection`,
`AnsibleNamespaceMetadata`). Also used to sync Pulp RBAC objects (Role, UserRole, GroupRole)
with DAB RBAC (RoleDefinition, RoleUserAssignment, RoleTeamAssignment).

The `Organization` model uses `@receiver(post_save)` on `Group`/`PulpGroup`/`BaseGroup` to
auto-create a `Team` whenever any group is created. The `_x_skip_create_team` hack flag
prevents infinite recursion when `Team.BEFORE_CREATE` creates its own group.

## Primary Key Conventions

- **Pulp-inherited models**: Use UUID PKs inherited from Pulp's `pulp_id` field. Do not add
  your own `id` field.
- **Galaxy-native models** (Namespace, LegacyNamespace, Organization, Team, AIIndexDenyList):
  Use Django's default `AutoField` integer PK.
- **Bridge models** (CollectionImport, ContainerDistroReadme, LegacyRoleDownloadCount,
  LegacyRoleSearchVector, LegacyRoleImport): Use `OneToOneField(primary_key=True)` pointing
  to the parent model, sharing its PK.

## Resource Registry (DAB)

Models that participate in the cross-service resource registry must have an
`AnsibleResourceField(primary_key_field="id")` field. Currently: `User`, `Group`,
`Organization`, `Team`. Of these, only `Organization` and `Team` are listed in
`ANSIBLE_BASE_RBAC_MODEL_REGISTRY` in settings.py with their `parent_field_name`. User and
Group have the resource field but are managed differently by DAB.

## Transaction Management

- **Model methods**: Use `@transaction.atomic` as a decorator for model methods that delete
  and recreate related objects (e.g., `Namespace.set_links`).
- **Classmethods**: `Setting.set_value_in_db` and `Setting.delete_*` wrap database writes
  in `@transaction.atomic`.
- **Serializer create/update**: Wrap multi-step create/update logic in `@transaction.atomic`
  (see namespace serializers, synclist serializers, EE serializers).
- **Viewset actions**: Wrap in `@transaction.atomic` when a single request touches multiple
  models (namespace create/update, group operations).
- **Management commands**: Use `with transaction.atomic():` around each bounded logical unit or chunk; use one transaction for the entire batch only when all-or-nothing behavior is required.
- **Access control mixins**: Permission assignment (`_set_groups`, `_set_users`) is wrapped
  in `@transaction.atomic` because it clears and re-adds all role assignments.

## Custom Managers

- **`SettingsManager`**: Overrides `create()` with distributed locking (Redis) and version
  management. Overrides `filter()` to be case-insensitive on `key`. Uses `bulk_create` with
  batch size 1000 for large operations.
- **`GroupManager`**: Adds `create_identity()` and `get_or_create_identity()` for scoped
  group names (`scope:name` format).
- **`OrganizationManager`**: Adds `get_default()` to retrieve the default organization.

## Migration Conventions

### Numbering and Naming
Migrations are sequentially numbered (`0001_` through `0059_`). Use descriptive names after
the number. Auto-generated migrations keep Django's default naming.

### Data Migrations
- Always use `apps.get_model("app_label", "ModelName")` -- never import models directly.
- Use `schema_editor.connection.alias` with `.using(db_alias)` for multi-database safety
  (see `0050_organization_data.py`).
- Data migrations should provide a `reverse_code`. Use `migrations.RunPython.noop` when reversal
  is not feasible rather than omitting it. Some early migrations omit reverse_code but this is
  discouraged.
- Complex data migration logic can be extracted to a helper module (see
  `galaxy_ng/app/migrations/_dab_rbac.py`).

### Cross-App Dependencies
Migrations frequently depend on `core`, `ansible`, `container`, and `dab_rbac` migrations.
Declare these explicitly in `dependencies`. Use `run_before` to ensure Galaxy migrations
execute before a specific upstream migration (see `0053_wait_for_dab_rbac` and
`0058_remove_galaxy_team_member_role`).

### Raw SQL
Use `RunSQL` only when ORM operations are insufficient (e.g., PostgreSQL triggers in
`0047_update_role_search_vector_trigger`, bulk data moves with explicit locking in `0012`).
Always provide `reverse_sql` (use `RunSQL.noop` if truly irreversible). Mark one-time
setup migrations as `elidable=True` so they are skipped during squashing.

### Elidable Migrations
Early migrations (`0003`, `0008`, `0009`, `0012`) mark data operations as `elidable=True`.
This signals they can be dropped during migration squashing since they only apply to
historical data states.

## PostgreSQL-Specific Features

- **Full-text search**: `LegacyRoleSearchVector` uses `SearchVectorField` with a `GinIndex`
  and a database trigger (created via `RunSQL`) that auto-updates the search vector on
  insert/update of `LegacyRole`.
- **Raw SQL in migrations**: `0012` uses PL/pgSQL functions with `LOCK TABLE ... IN ACCESS
  EXCLUSIVE MODE` for safe bulk content moves between repositories.

## Query Patterns

- Use `select_related()` for FK traversals in hot paths (e.g., EE viewsets joining namespace).
- Use `prefetch_related()` for reverse FK / M2M relationships (e.g., manifest tags,
  repository content).
- Use `select_for_update()` for counter increments (`LegacyRoleDownloadCount`).
- Use `.distinct("key_lower")` with `.order_by("key_lower", "-version")` for
  latest-version-per-key queries (see `Setting.get_all`).

## Timestamp Field Conventions

Two patterns exist; follow the one matching the model's lineage:
- **Galaxy-native models**: `created = DateTimeField(auto_now_add=True)`,
  `modified/updated = DateTimeField(auto_now=True)`.
- **DAB abstract models** (Organization, Team): Inherited `created`/`modified` fields from
  `AbstractOrganization`/`AbstractTeam` with `auto_now_add`/`auto_now` after migration 0051.

Do not use `created_on`/`modified_on` -- these were renamed in migration 0051.

## Access Control Mixins

`GroupModelPermissionsMixin` and `UserModelPermissionsMixin` add `groups`/`users` properties
that proxy Pulp's role-based permission system. They use a deferred-write pattern: during
object creation (`_state.adding`), permission data is stored in `_groups`/`_users` instance
attributes and applied via the `after_save` hook once the object has a PK. For proxy models,
the mixin resolves to the concrete model via `_meta.concrete_model` before assigning
permissions, because Pulp does not support role assignment on proxy models.
