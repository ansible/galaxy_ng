# OpenAPI Specification Validation

## Overview

This repository includes CI checks to validate the static OpenAPI specification
file (`galaxy_ng/app/static/galaxy.json`) on every pull request.

## What is Validated

- OpenAPI 3.x schema compliance
- Valid JSON structure
- Required fields (paths, info, openapi version)
- Schema reference validity

## CI Behavior

- **Errors**: Block the PR (validation fails)
- **Warnings**: Logged but don't block the PR

## Running Locally

To validate the spec locally before submitting a PR:

```bash
make validate-openapi
```

Or manually:

```bash
pip install openapi-spec-validator
openapi-spec-validator galaxy_ng/app/static/galaxy.json
```

To see all validation errors (instead of just the best match):

```bash
openapi-spec-validator galaxy_ng/app/static/galaxy.json --errors all
```

## Common Errors and Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `Missing required field 'operationId'` | Endpoint lacks operationId | Add unique operationId to the operation |
| `Invalid $ref` | Schema reference not found | Check the $ref path in components/schemas |
| `Duplicate operationId` | Two operations share the same ID | Make operationIds unique |
| `'...' is not a 'date-time'` | Default value doesn't match RFC 3339 format | Use format `YYYY-MM-DDTHH:MM:SSZ` or remove the default |

## Related Documentation

- [OpenAPI 3.0.3 Specification](https://spec.openapis.org/oas/v3.0.3)