# Galaxy NG

<img align="left" width="150" src="https://raw.githubusercontent.com/ansible/logos/be211ebccc316652eb725db688e75d932f8fa073/galaxy/galaxy-logo.svg">

[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=ansible_galaxy_ng&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=ansible_galaxy_ng)
[![Build Status](https://github.com/ansible/galaxy_ng/actions/workflows/ci-docker-compose-integration.yml/badge.svg)](https://github.com/ansible/galaxy_ng/actions/workflows/ci-docker-compose-integration.yml)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=ansible_galaxy_ng&metric=coverage)](https://sonarcloud.io/summary/new_code?id=ansible_galaxy_ng)

A Pulp plugin to support hosting your very own Ansible Galaxy server.

Our mission is to help organizations share Ansible automation and promote a culture of collaboration around Ansible automation development. We'll be providing features that make it easy to create, discover, use and distribute Ansible automation content.

## Tech Stack

- **Framework:** Django + Django REST Framework, running as a [Pulp](https://pulpproject.org/) plugin
- **Async Tasks:** Pulp tasking system (RQ workers with resource locking)
- **Database:** PostgreSQL
- **Configuration:** Dynaconf (settings loaded from multiple sources with `PULP_` env var prefix)
- **Access Control:** Dual RBAC system (legacy Pulp access policies + django-ansible-base DAB RBAC)

To learn more about Pulp, [view the Pulp project page](https://pulpproject.org/).

## Project Structure

```
galaxy_ng/
  app/
    models/              # Galaxy-native models (Namespace, User, Organization, etc.)
    api/
      v1/                # Legacy roles API
      v3/                # Main Galaxy API (collections, namespaces, EE, tasks)
      ui/v1/, ui/v2/     # UI-optimized endpoints
    access_control/      # Access policies and RBAC statements
    tasks/               # Async Pulp tasks (publishing, signing, sync, etc.)
    auth/                # Authentication backends
    settings.py          # Settings fragment (merged via Dynaconf)
    dynaconf_hooks.py    # Post-load conditional settings
  tests/
    unit/                # Unit tests (real DB, DRF APIClient)
    integration/         # Integration tests (require running compose stack)
```

For the full structure and architectural details, see [AGENTS.md](AGENTS.md).

## Documentation

Project documentation is hosted on [Read The Docs](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/).

## OpenAPI Spec

View the latest version of the spec at <https://galaxy.ansible.com/api/v3/swagger-ui/>. *(Directlink to [JSON](https://galaxy.ansible.com/api/v3/openapi.json) or [YAML](https://galaxy.ansible.com/api/v3/openapi.yaml))*

### Static OpenAPI Spec for AAP

This repository provides a **static, curated OpenAPI specification** (`galaxy.json`) that contains user-facing endpoints with AI-friendly metadata.

The static spec differs from the dynamically generated spec above in that it:
- Includes only user-facing endpoints (87 paths vs. 559 in the full spec)
- Contains `x-ai-description` fields for AI/MCP tool integration
- Serves as the source of truth for Hub's API specification in AAP

## Code Coverage

This project uses both SonarCloud and Codecov for code coverage tracking:

### SonarCloud
- **Public Coverage:** Available at [SonarCloud](https://sonarcloud.io/summary/new_code?id=ansible_galaxy_ng)
- **Badge Integration:** Coverage metrics displayed in README badges above
- **Configuration:** Managed through `sonar-project.properties`

### Codecov
- **Purpose:** Internal coverage tracking
- **Coverage Configuration:** `codecov.yml` (aligned with `sonar-project.properties` exclusions)  
- **CI Integration:** Coverage uploads automatically on main branch pushes
- **Flags:** `unit-tests` flag tracks unit test coverage separately

## Communication

Refer to the [Communication](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/community/overview/#communication)
section of the Contributor Guide to find out how to get in touch with us.

You can also find more information in the
[Ansible communication guide](https://docs.ansible.com/ansible/devel/community/communication.html).

## Documentation for AI Agents

This repository includes structured guidance for AI coding agents in [AGENTS.md](AGENTS.md), covering architecture, conventions, and common pitfalls. Domain-specific guidelines live in `docs/`:

| Guide | Topics |
|-------|--------|
| [Security](docs/security-guidelines.md) | Access policies, RBAC, authentication, input validation |
| [API Contracts](docs/api-contracts-guidelines.md) | API versions, viewsets, serializers, backward compatibility |
| [Database](docs/database-guidelines.md) | Model patterns, migrations, query conventions |
| [Error Handling](docs/error-handling-guidelines.md) | Exception handler, ValidationError usage, logging |
| [Performance](docs/performance-guidelines.md) | Task dispatch, resource locking, query optimization |
| [Testing](docs/testing-guidelines.md) | Unit/integration test structure, fixtures, markers |
| [Integration](docs/integration-guidelines.md) | Pulp tasks, signal handlers, external services |

## Contributing

* If you're interested in jumping in and helping out, [view the contributing guide](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/dev/getting_started/).
* To setup your development environment, [view the development setup guide](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/dev/getting_started/#setting-up-the-developer-environment).
* Found a bug or have a feature idea? Please [open an issue](https://issues.redhat.com/projects/AAH/issues).

## Run it

```console
$ docker compose -f dev/compose/standalone.yaml up
```

[more details](https://github.com/ansible/galaxy_ng/blob/main/dev/compose/README.md)

## Code of Conduct

Please see the official
[Ansible Community Code of Conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html).

## License

GNU General Public License v2. View [LICENSE](/LICENSE) for full text.
