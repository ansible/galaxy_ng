# Continuous Integration

Galaxy NG uses GitHub Actions for continuous integration testing. The CI pipeline runs linting, unit tests, and integration tests on every pull request and push to main or stable branches.

## CI Pipelines

The main CI workflows are located in `.github/workflows/`:

- **ci_full.yml**: Runs linting, unit tests, and uploads coverage to SonarCloud
- **ci-docker-compose-integration.yml**: Runs integration tests across multiple deployment profiles
- **ci_automation_hub_collection.yml**: Tests the ansible_hub collection integration
- **sonar-pr.yaml**: Handles SonarCloud analysis for pull requests

## Python Version Matrix

The CI pipeline runs unit tests across multiple Python versions using GitHub Actions matrix builds.

**Current Python versions tested**: 3.11, 3.12

### Adding a New Python Version

To add support for a new Python version (e.g., 3.13):

1. **Update `tox.ini`** in the repository root:
   ```ini
   env_list =
       py311
       py312
       py313  # Add new version
   ```

2. **Update `.github/workflows/ci_full.yml`**:
   ```yaml
   matrix:
     python-version: ["3.11", "3.12", "3.13"]  # Add new version
   ```

That's it! The rest of the configuration is designed to be extensible:

- **Dynamic tox environment naming**: Version numbers are automatically converted to tox environment names (3.13 → py313)
- **Coverage artifacts**: Only uploaded from the latest Python version (currently 3.12) to save storage and simplify reporting
- **Parallel execution**: Tests run in parallel across all versions with `fail-fast: false`
- **Reporting**: SonarCloud and jUnit uploads use Python 3.12 by default (see below for how to change)

### Why Only Upload Coverage from the Latest Python Version?

The CI uploads test coverage artifacts only from Python 3.12 (the latest supported version), not from all matrix versions. This is intentional:

- **Code coverage is version-agnostic**: Coverage measures which lines of code are executed during tests, not Python-specific behavior. The coverage from 3.12 accurately represents what's tested across all versions.
- **Saves storage**: Coverage XML files are uploaded as artifacts. Only uploading one saves GitHub Actions storage quota.
- **Simplifies SonarCloud integration**: SonarCloud only needs one coverage report for analysis.
- **Future-focused**: Using the latest Python version ensures our coverage analysis reflects modern Python behavior and features.

If you need coverage from a specific Python version for debugging, you can always run tox locally: `tox -e py311` generates `coverage.xml` locally.

### Changing the Python Version for Coverage/SonarCloud/jUnit Reporting

The workflow defines a `PRIMARY_PYTHON_VERSION` environment variable at the top of `.github/workflows/ci_full.yml`. This variable controls which Python version is used for coverage uploads, SonarCloud analysis, and jUnit reporting.

To change the version (e.g., when promoting 3.13 as the primary version), update the variable:

```yaml
env:
  PRIMARY_PYTHON_VERSION: "3.13"
```

**Important:** When adding or removing Python versions, you must also update the matrix array in the `test` job. GitHub Actions doesn't support env vars in matrix definitions, so the matrix must be updated separately.

This variable is referenced by:
- Coverage artifact upload
- SonarCloud scan
- jUnit XML test results upload

**Note:** You don't need to update `.github/workflows/sonar-pr.yaml` - the artifact is always named `coverage` regardless of which Python version uploads it. This maintains backward compatibility with the workflow_run trigger.

### Testing Locally with Multiple Python Versions

To test with a specific Python version locally:

```bash
# Test with Python 3.11
tox -e py311

# Test with Python 3.12
tox -e py312

# Run all environments
tox
```

## Integration Tests

Integration tests run across multiple deployment profiles to ensure Galaxy NG works correctly in different configurations. See the [integration test documentation](../tests/integration.md) for more details.

## Triggering CI

CI runs automatically on:
- Every pull request
- Pushes to `main` and `stable-*` branches
- Daily at 3:00 UTC (scheduled run)
- Manual workflow dispatch

You can also trigger workflows manually from the GitHub Actions tab in the repository.
