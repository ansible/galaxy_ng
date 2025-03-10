# Galaxy NG

<img align="left" width="150" src="https://raw.githubusercontent.com/ansible/logos/be211ebccc316652eb725db688e75d932f8fa073/galaxy/galaxy-logo.svg">

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=ansible_galaxy_ng&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=ansible_galaxy_ng)
[![Build Status](https://github.com/ansible/galaxy_ng/actions/workflows/ci-docker-compose-integration.yml/badge.svg)](https://github.com/ansible/galaxy_ng/actions/workflows/ci-docker-compose-integration.yml)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=ansible_galaxy_ng&metric=coverage)](https://sonarcloud.io/summary/new_code?id=ansible_galaxy_ng)

A Pulp plugin to support hosting your very own Ansible Galaxy server.

Our mission is to help organizations share Ansible automation and promote a culture of collaboration around Ansible automation development. We'll be providing features that make it easy to create, discover, use and distribute Ansible automation content.

To learn more about Pulp, [view the Pulp project page](https://pulpproject.org/).

## Documentation

Project documentation is hosted on [Read The Docs](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/).

## OpenAPI Spec

View the latest version of the spec at <https://galaxy.ansible.com/api/v3/swagger-ui/>. *(Directlink to [JSON](https://galaxy.ansible.com/api/v3/openapi.json) or [YAML](https://galaxy.ansible.com/api/v3/openapi.yaml))*

## Communication

Refer to the [Communication](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/community/overview/#communication)
section of the Contributor Guide to find out how to get in touch with us.

You can also find more information in the
[Ansible communication guide](https://docs.ansible.com/ansible/devel/community/communication.html).

## Contributing

* If you're interested in jumping in and helping out, [view the contributing guide](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/dev/getting_started/).
* To setup your development environment, [view the development setup guide](https://ansible.readthedocs.io/projects/galaxy-ng/en/latest/dev/getting_started/#setting-up-the-developer-environment).
* Found a bug or have a feature idea? Please [open an issue](https://issues.redhat.com/projects/AAH/issues).

## Run it

```console
$ docker compose -f dev/compose/standalone.yaml up
```

[more details](https://github.com/ansible/galaxy_ng/blob/master/dev/compose/README.md)

## Code of Conduct

Please see the official
[Ansible Community Code of Conduct](https://docs.ansible.com/ansible/devel/community/code_of_conduct.html).

## License

GNU General Public License v2. View [LICENSE](/LICENSE) for full text.
