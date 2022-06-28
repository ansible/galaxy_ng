# Developer Guidelines

## Understanding the Galaxy NG Rest API

The API in the developer environment will either be served under `/api/galaxy/` or `/api/automation-hub/`.
Visiting this endpoint shows that there are two versions available: `v3/` and `pulp/api/v3/`. Understanding
the purpose of each of these APIs is crucial when contributing new features to the backend.

### v3/

This is the original galaxy_ng API. It is primarily used for content consumption and to fill in some client
specific gaps that the pulp APIs can't support. API endpoints should be added here that:

- Provide interfaces for content consumption. Some clients, such as `ansible-galaxy`, require a
  specific API layout to function. Other clients, such as the UI, require more data rich APIs that
  pull together data from several pulp models.
    - Examples:
        - Execution environment search - provides a level of abstraction on top of the vanilla EE APIs from
          pulp-container that make them much easier for the UI to consume.
        - Collection search
        - Collection downloads - provides the APIs needed to drive the `ansible-galaxy` CLI.
- Provide client operations.
    - Examples:
        - Token generation. Pulpcore doesn't support API tokens, but they are needed by `ansible-galaxy`.
        - UI Authentication. The APIs for authenticating pulp don't support JSON.
        - Configuration. The UI needs to know more information about the backend's configuration than the
          pulp APIs can provide.
- Provide content specific operations.
    - Collection Deprecation
    - EE/Collection Deletion - Content deletion is a high level operation that requires many individual
      steps on the pulp API. These endpoints provide a nice abstraction on top of a lot of lower level
      pulp operations.

### pulp/api/v3/

These APIs are provided by pulpcore and can be extended by other plugins (including galaxy_ng). These should
be used for managing pulp primitives. This includes:

- General content operations
  - Moving, copying and syncing content between repositories.
- Manging any pulp primitives. This includes:
  - Repos
  - Remotes
  - Distributions
  - Groups
  - Users
  - RBAC Roles
  - Tasks
  - Pretty much anything else defined in [the pulpcore models](https://github.com/pulp/pulpcore/tree/main/pulpcore/app/models).
