# Feature Flags

Some features are disabled by default. You can enable them by setting the
feature flag under `GALAXY_FEATURE_FLAGS` setting.

Example for enabling EEs endpoints:

`via environment variables`
```bash
export PULP_GALAXY_FEATURE_FLAGS__execution_environments=true
```
`via /etc/pulp/settings.py`
```python
GALAXY_FEATURE_FLAGS__execution_environments = True

# Alternatively
GALAXY_FEATURE_FLAGS = {
  "dynaconf_merge": True,
  "execution_environments": True
}
```

The same pattern can be used for the following feature flags:

- `signatures_enabled`
    - boolean
    - Enable the signing feature
    - default: False (or turned true whenever a Signing Service is set)
- `require_upload_signatures`
    - boolean
    - Require a signature to be upload before collection approval
    - default: value of GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL setting.
- `can_create_signatures`
    - boolean
    - Tells UI to show the signing buttons
    - default: signatures_enabled AND Signing Service is set AND keys present
- `can_upload_signatures`
    - boolean
    - Tells UI to show the upload signature button
    - default: signatures_enabled AND GALAXY_REQUIRE_SIGNATURE_FOR_APPROVAL
- `collection_auto_sign`
    - boolean
    - Set the signature to be created automatically when collection is approved
    - Default: value of GALAXY_AUTO_SIGN_COLLECTIONS setting.
- `display_signatures`
    - boolean
    - Tells UI to show the signature information on badges
    - default: signatures_enabled AND (can create or can upload)
- `execution_environments`
    - boolean
    - Tells UI to show the execution environments tab and enable EE endpoints
    - default: False
- `container_signing`
    - boolean
    - Tells UI to show the container signing buttons and badges
    - default: True when Container Signing Service is configured
- `ai_deny_index`
    - boolean
    - Enables AI Deny Index endpoints and tells UI to display the Wisdom opt-out buttons
    - default: False
- `display_repositories`
    - boolean
    - Signals the UI to show or not to show repository information.
    - default: True
