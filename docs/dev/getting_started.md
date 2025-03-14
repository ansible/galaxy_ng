# Getting Started

## GalaxyNG Basics

- [Overview](developer_guide/overview.md)
- [Data Models](developer_guide/data_models.md)
- [REST API](developer_guide/rest_api.md)
- [Services](developer_guide/services.md)
- [RBAC](developer_guide/rbac.md)

## Issue Tracker

Issues for Galaxy NG are tracked in Jira at https://issues.redhat.com/browse/AAH. Issues labeled with [quickfix](https://issues.redhat.com/browse/AAH-1202?jql=project%20%3D%20AAH%20AND%20resolution%20%3D%20Unresolved%20AND%20labels%20%3D%20quickfix%20ORDER%20BY%20priority%20DESC%2C%20updated%20DESC) are a good place for beginners to get started.

## Submitting a Pull Request

UI PRs should be submitted at [github.com/ansible/ansible-hub-ui](https://github.com/ansible/ansible-hub-ui).

When submitting a PR to either the UI or backend:

- All PRs must include either `Issue: AAH-XXXX` or `No-Issue` in the commit message.

    - `No-Issue` should be used infrequently and the reviewers may ask you to create a Jira ticket and attach it to your PR.
    - `Issue: AAH-XXXX` should must include a Jira ticket number (such as AAH-123). This also requires a changelog entry in `CHANGES/`. Changelog entries follow the `<issue_number>.type` format. For example if I submit a fix for AAH-123, it must also come with a `CHANGES/123.bugfix` entry. Changelog file extensions include:

        - `.feature`: use this for new features. New features must include documentation. See our [docs documentation](writing_docs.md) for more information.
        - `.bugfix`: use this for bugfixes.
        - `.misc`: use this for small maintenance changes that don't need to be communicated such as fixing typos, refactoring code etc.

PRs for the backend also require:

- All commits must be signed. [How to set up commit signing](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits).
- Any changes to the app require updates to the tests in `galaxy_ng/tests/`. This can include adding new tests or updating existing tests to cover changes. See [dev/writing_tests] for more information.
PRs will be reviewed by two members of the team.

## Setting up the developer environment

### Docker Compose

[Docker Compose Env developer setup guide](docker_environment.md)
