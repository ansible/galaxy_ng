TL;DR:

```bash
# Backup
cp galaxy_ng/app/static/galaxy.json galaxy_ng/app/static/galaxy.json.bck
cp galaxy_ng/app/static/descriptions.yaml galaxy_ng/app/static/descriptions.yaml.bck
cp galaxy_ng/app/static/tags.yaml galaxy_ng/app/static/tags.yaml.bck

# Shorten the IDS (probably need to run only once)
# python galaxy_ng/app/utils/apispec/id_fix.py galaxy_ng/app/static/galaxy.json > /tmp/galaxy.json
# mv /tmp/galaxy.json galaxy_ng/app/static/galaxy.json

# Extract description from JSON to YAML
python galaxy_ng/app/utils/apispec/extract_descriptions.py galaxy_ng/app/static/galaxy.json > galaxy_ng/app/static/descriptions.yaml
```

When descriptions file is edited, update the JSON spec with the edits.

```bash
# Update JSON from YAML (edited descriptions) [remove the --diff-only to apply]
python galaxy_ng/app/utils/apispec/update_descriptions.py galaxy_ng/app/static/descriptions.yaml galaxy_ng/app/static/galaxy.json --diff-only
```

When tags file is edited, update the JSON spec with the edits.

```bash
# Update JSON from YAML (edited tags) [remove the --diff-only to apply]
python galaxy_ng/app/utils/apispec/update_tags.py galaxy_ng/app/static/tags.yaml galaxy_ng/app/static/galaxy.json --diff-only
```

Q: What if a new endpoint is added to the `galaxy.json` spec, how to get `descriptions.yaml` updated?

Option1: Manually edit it
Option2: Run the extract_descriptions script without pointing to a temp file `> /tmp/new.yaml` now use any diff tool you prefer to merge the diffs. e.g: `meld` 


# OpenAPI Spec Utilities

This directory contains scripts for managing the OpenAPI specification file (`galaxy_ng/app/static/galaxy.json`).

## Overview

These utilities help maintain the OpenAPI spec by:

1. **Shortening operation IDs** for MCP tool name generation (hard limit of 64 characters)
2. **Managing endpoint descriptions** through a human-editable YAML file
3. **Managing endpoint tags** through a human-editable YAML file for categorizing endpoints by project area

## Scripts

### 1. id_fix.py - Operation ID Transformation

Transforms long, auto-generated operation IDs into shorter, meaningful identifiers while maintaining uniqueness.

#### Usage

```bash
# Transform IDs and output to stdout
python id_fix.py galaxy.json

# Transform and save to a new file
python id_fix.py galaxy.json > galaxy_fixed.json

# Overwrite the original file
python id_fix.py galaxy.json > temp.json && mv temp.json galaxy.json
```

#### Transformation Rules

The script applies the following rules in order:

1. **Deprecated Prefix**: If the endpoint has `deprecated: true`, the ID is prefixed with `deprecated_`

2. **Pulp Marker**: If the path contains `/pulp/`, the ID includes `pulp_`

3. **Version Marker**: If the path contains a version segment (`/v1/`, `/v2/`, `/v3/`), the ID includes `v1_`, `v2_`, or `v3_`

4. **UI Marker**: If the path contains `/_ui/`, the ID includes `ui_`

5. **Feature Area Extraction**: The meaningful part of the path (after version/plugin/ui markers) becomes the core of the ID

6. **Noise Word Removal**: The following words are filtered out as they don't add meaning:
   - `api`
   - `galaxy`
   - `plugin`
   - `pulp_ansible`
   - `default`
   - Template parameters (e.g., `{id}`, `{pulp_id}`, `{path}`)

7. **Consecutive Duplicate Removal**: Words that appear consecutively are deduplicated
   - `ansible_ansible` → `ansible`

8. **Action Suffix**: Based on the HTTP method and path structure:
   - `GET` → `_get`
   - `POST` → `_post`
   - `PUT` → `_put`
   - `PATCH` → `_patch`
   - `DELETE` → `_delete`
   - Special path actions override the method: `_sync`, `_sign`, `_download`, `_upload`, `_rebuild`, `_curate`, `_index`, `_avatar`

9. **Transfer Action Suffix**: If the path or current operationID contains `upload` or `download` anywhere, the generated ID must end with `_upload` or `_download` respectively. This ensures transfer-related endpoints are clearly identified regardless of where the keyword appears.

10. **Uniqueness Enforcement**: If duplicate IDs are detected, numeric suffixes are added (`_2`, `_3`, etc.)

#### Examples

| Original Path | Method | Original ID | Transformed ID |
|--------------|--------|-------------|----------------|
| `/ansible/collections/` (deprecated) | POST | `upload_collection` | `deprecated_ansible_collections_post` |
| `/api/galaxy/` | GET | `api_galaxy_read` | `root_get` |
| `/api/galaxy/_ui/v1/auth/login/` | GET | `api_galaxy__ui_v1_auth_login_get` | `v1_ui_auth_login_get` |
| `/api/galaxy/_ui/v1/auth/logout/` | POST | `api_galaxy__ui_v1_auth_logout_post` | `v1_ui_auth_logout_post` |
| `/api/galaxy/_ui/v1/namespaces/{name}/` | GET | `api_galaxy__ui_v1_namespaces_read` | `v1_ui_namespaces_get` |
| `/api/galaxy/pulp/api/v3/repositories/ansible/{pulp_id}/sync/` | POST | `repositories_ansible_ansible_sync` | `pulp_v3_repositories_ansible_sync` |
| `/api/galaxy/v3/namespaces/` | GET | `api_galaxy_v3_namespaces_list` | `v3_namespaces_get` |

#### Idempotency

The script is designed to be idempotent - running it multiple times on the same input produces identical output. This is achieved by:

- Deriving actions from path structure, not from the current operation ID
- Using deterministic ordering for duplicate resolution

#### Performance

The script uses Python's `asyncio` for concurrent transformation of operation IDs, though the actual benefit is minimal for typical spec sizes.

---

### 2. extract_descriptions.py - Description Extraction

Extracts operation ID to description mappings from the OpenAPI spec into a YAML file for easy editing.

#### Usage

```bash
# Extract to stdout
python extract_descriptions.py galaxy.json

# Extract to file
python extract_descriptions.py galaxy.json > descriptions.yaml
```

#### Output Format

The output is a YAML file with operation IDs as keys and descriptions as values:

```yaml
api_galaxy__ui_v1_auth_login_get: Authenticate and manage tokens
api_galaxy__ui_v1_auth_login_post: Authenticate and manage tokens
api_galaxy__ui_v1_namespaces_list: Get collection namespaces
upload_collection: |
  Deprecated. Superseded by `/api/galaxy/v3/artifacts/collections/`.
  Create an artifact and trigger an asynchronous task to create
  Collection content from it.
```

#### Description Priority

The script prefers `x-ai-description` over `description` when both are present. This allows maintaining separate human-readable descriptions for AI/MCP consumption.

---

### 3. update_descriptions.py - Description Updates

Updates the OpenAPI spec with descriptions from a YAML file. Only modified descriptions are updated.

#### Usage

```bash
# Preview changes (dry run)
python update_descriptions.py descriptions.yaml galaxy.json --diff-only

# Apply changes
python update_descriptions.py descriptions.yaml galaxy.json
```

#### Options

| Option | Description |
|--------|-------------|
| `--diff-only` | Show what would be changed without modifying the file |

#### Output

The script prints a summary of changes:

```
============================================================
Changes: 3 description(s) would be updated
============================================================

Operation: api_galaxy__ui_v1_auth_login_get
  Path: /api/galaxy/_ui/v1/auth/login/
  Method: GET
  Old: Authenticate and manage tokens
  New: Login to the Galaxy API and obtain an authentication token

...

Updated 3 description(s) in galaxy.json
```

#### Behavior

- Only descriptions that differ (after whitespace normalization) are updated
- If `x-ai-description` exists in the spec, it is updated; otherwise `description` is updated
- Unknown operation IDs in the YAML file trigger a warning but don't cause failure
- The original file is modified in-place (back up before running)

---

### 4. update_tags.py - Tag Updates

Updates the OpenAPI spec with tags from a YAML file. Only modified tags are updated.

#### Usage

```bash
# Preview changes (dry run)
python update_tags.py tags.yaml galaxy.json --diff-only

# Apply changes
python update_tags.py tags.yaml galaxy.json
```

#### Options

| Option | Description |
|--------|-------------|
| `--diff-only` | Show what would be changed without modifying the file |

#### Output

The script prints a summary of changes:

```
============================================================
Changes: 3 tag(s) would be updated
============================================================

Operation: v1_ui_auth_login_get
  Path: /api/galaxy/_ui/v1/auth/login/
  Method: GET
  Old: ['Api: _Ui V1 Auth Login']
  New: ['Access']

...

Updated 3 tag(s) in galaxy.json
```

#### Behavior

- Only tags that differ (after sorting) are updated
- Unknown operation IDs in the YAML file trigger a warning but don't cause failure
- The original file is modified in-place (back up before running)

---

## File: descriptions.yaml

Located at `galaxy_ng/app/static/descriptions.yaml`, this file stores the mapping between operation IDs and their descriptions.

### Format

```yaml
# Single-line descriptions
operation_id_1: Short description here

# Multi-line descriptions (use literal block scalar)
operation_id_2: |
  This is a longer description that spans
  multiple lines. The pipe character preserves
  line breaks exactly as written.

# Folded multi-line (collapses to single line)
operation_id_3: >
  This description will be folded into
  a single line when parsed, with spaces
  between the original lines.
```

### Workflow

1. **Initial extraction**: Run `extract_descriptions.py` to create the YAML file
2. **Edit descriptions**: Modify the YAML file in any text editor
3. **Preview changes**: Run `update_descriptions.py --diff-only` to see what will change
4. **Apply changes**: Run `update_descriptions.py` to update the JSON spec

---

## File: tags.yaml

Located at `galaxy_ng/app/static/tags.yaml`, this file stores the mapping between operation IDs and their tags.

### Format

```yaml
# Single tag
operation_id_1:
  - Collections

# Multiple tags
operation_id_2:
  - Signing
  - Collections

# With comments for organization
# Authentication endpoints
"v1_ui_auth_login_get":
  - Access
"v1_ui_auth_logout_post":
  - Access
```

### Available Tags

The following tags represent project areas/features:

| Tag | Description |
|-----|-------------|
| Info | API root endpoints, status checks |
| Access | Authentication, login/logout, tokens |
| Namespaces | Namespace CRUD operations |
| Collections | Collection artifacts, versions, search, imports |
| Content Sync | Sync operations, synclists, repository sync |
| Container/Execution Environments | EE registries, repositories, remotes |
| Tasks | Async task status, import tasks |
| Remotes | Collection and EE remotes management |
| Config | Client configuration, settings, repository config |
| Feature Flags | Feature flag states |
| Resource Registry | EE registries |
| Signing | Collection signatures, signing services |

### Workflow

1. **Edit tags**: Modify the YAML file in any text editor
2. **Preview changes**: Run `update_tags.py --diff-only` to see what will change
3. **Apply changes**: Run `update_tags.py` to update the JSON spec

---

## Best Practices

### Operation ID Naming

When manually adding new endpoints, follow these conventions:

1. Keep IDs under 40 characters when possible (hard limit: 64)
2. Use the pattern: `[deprecated_][pulp_][vN_][ui_]<resource>_<method>`
3. Use lowercase with underscores
4. Use HTTP method names as suffixes (`get`, `post`, `put`, `patch`, `delete`)
5. Avoid redundant words

### Description Writing

1. Keep descriptions concise but informative
2. Start with a verb (Get, Create, Update, Delete, List, etc.)
3. Mention deprecation status if applicable
4. Include the replacement endpoint for deprecated APIs

---

## Dependencies

These scripts use only standard library modules and packages already in `requirements/requirements.common.txt`:

- `json` (standard library)
- `asyncio` (standard library)
- `re` (standard library)
- `sys` (standard library)
- `argparse` (standard library)
- `yaml` (PyYAML - in requirements)

---

## Related Documentation

- [OpenAPI Validation](../../../docs/dev/openapi_validation.md) - CI validation requirements
- [OpenAPI 3.0.3 Specification](https://spec.openapis.org/oas/v3.0.3) - Official spec
- [AAP-56276](https://issues.redhat.com/browse/AAP-56276) - Operation ID length requirements
- [AAP-56274](https://issues.redhat.com/browse/AAP-56274) - Description management requirements
