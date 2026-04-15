# Insights Fixture Data

`insights-fixture.tar.gz` contains a PostgreSQL database dump (`pulp_db.backup`)
and Pulp media artifacts used by the `certified-sync` docker compose profile.
The `load-sync-data` service restores this fixture into the insights-side
database before migrations run.

The fixture provides pre-loaded collections, deprecations, signatures, and test
users so that sync tests have a source environment to pull from.

## When to regenerate

Regenerate the fixture when upgrading pulpcore, pulp_ansible, or pulp_container
to versions that include new or squashed migrations. If the fixture's migration
state doesn't match the installed code, `pulpcore-manager migrate` will fail
with `InconsistentMigrationHistory`.

## How to regenerate

### 1. Start a fresh insights database

```bash
docker compose -f dev/compose/certified-sync.yaml down -v
docker compose -f dev/compose/certified-sync.yaml up -d insights-postgres
```

Wait for postgres to be healthy.

### 2. Restore the old fixture

```bash
docker compose -f dev/compose/certified-sync.yaml up load-sync-data
```

This loads the existing collections and test data into the database.

### 3. Fix migration state if needed

If the old fixture has stale migration records (e.g., individual migrations
that have since been squashed), insert the required records. For example,
pulpcore 3.85+ squashed migrations 0001-0090:

```bash
docker run --rm --network compose_default \
  -e PGPASSWORD=galaxy_ng \
  postgres:16 \
  psql -h insights-postgres -U galaxy_ng -d galaxy_ng -c "
    INSERT INTO django_migrations (app, name, applied)
    SELECT 'core', '0001_squashed_0090_char_to_text_field', NOW()
    WHERE NOT EXISTS (
      SELECT 1 FROM django_migrations
      WHERE app = 'core' AND name = '0001_squashed_0090_char_to_text_field'
    );
  "
```

### 4. Run migrations

```bash
docker run --rm --network compose_default \
  -v "$PWD/../../..:/src" \
  -v "$PWD/../..:/app" \
  -e PULP_DATABASES__default__HOST=insights-postgres \
  -e PULP_DATABASES__default__ENGINE=django.db.backends.postgresql \
  -e PULP_DATABASES__default__NAME=galaxy_ng \
  -e PULP_DATABASES__default__USER=galaxy_ng \
  -e PULP_DATABASES__default__PASSWORD=galaxy_ng \
  -e PULP_DATABASES__default__PORT=5432 \
  -e PULP_GALAXY_DEPLOYMENT_MODE=insights \
  -e PULP_RH_ENTITLEMENT_REQUIRED=insights \
  -e PULP_GALAXY_API_PATH_PREFIX=/api/automation-hub/ \
  -e PULP_CONTENT_PATH_PREFIX=/api/automation-hub/pulp/content/ \
  -e PULP_ANSIBLE_API_HOSTNAME=http://localhost:1234 \
  -e PULP_ANSIBLE_CONTENT_HOSTNAME=http://localhost:1234 \
  -e PULP_CONTENT_ORIGIN=http://localhost:1234 \
  -e PULP_RESOURCE_SERVER_SYNC_ENABLED=false \
  -e PULP_ANSIBLE_BASE_ROLES_REQUIRE_VIEW=false \
  -e PULP_GALAXY_FEATURE_FLAGS__dab_resource_registry=false \
  -e PULP_GALAXY_AUTHENTICATION_CLASSES="['galaxy_ng.app.auth.auth.RHIdentityAuthentication']" \
  -e LOCK_REQUIREMENTS=0 \
  -e PULP_ANALYTICS=false \
  -e PULP_DEFAULT_FILE_STORAGE="pulpcore.app.models.storage.FileSystem" \
  -e DEV_SOURCE_PATH="${DEV_SOURCE_PATH}" \
  --user root \
  localhost/galaxy_ng/galaxy_ng:dev \
  bash -c "/src/galaxy_ng/dev/compose/bin/devinstall && pulpcore-manager migrate"
```

### 5. Dump the upgraded database

```bash
docker run --rm --network compose_default \
  -v "$PWD:/db_data" \
  -e PGPASSWORD=galaxy_ng \
  postgres:16 \
  pg_dump -h insights-postgres -U galaxy_ng -d galaxy_ng \
    -Fc -f /db_data/pulp_db.backup
```

### 6. Package the new fixture

Rebuild the tarball with the old media artifacts and new database dump:

```bash
docker run --rm \
  -v "$PWD:/db_data" \
  --user root \
  postgres:16 \
  bash -c "
    mkdir -p /tmp/build && cd /tmp/build
    tar xzf /db_data/insights-fixture.tar.gz
    cp /db_data/pulp_db.backup ./pulp_db.backup
    tar czf /db_data/insights-fixture.tar.gz .
  "
rm pulp_db.backup
```

### 7. Verify

Tear down and start the full certified-sync stack:

```bash
docker compose -f dev/compose/certified-sync.yaml down -v
docker compose -f dev/compose/certified-sync.yaml up insights-migrations
```

Migrations should complete with "No migrations to apply."

## Contents

The fixture includes:
- 8 collection versions across 6 namespaces (ansible, cisco, dellemc, ibm, infinidat)
- At least 1 deprecated collection
- At least 1 signed collection
- Collection artifacts in `media/artifact/`
- Test user accounts (created by `setup_test_data.py`)

## History

- **Dec 2022** (PR #1551): Original fixture created by David Newswanger for CRC sync CI tests
- **Jan 2025** (PR #2405): Incorporated into docker compose certified-sync profile
- **Apr 2026**: Regenerated for pulpcore 3.105.2 upgrade (squashed migration fix)
