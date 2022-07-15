# Overview

## Key Technologies

Galaxy NG relies on the following dependencies:

- [Pulp](https://pulpproject.org/): software repository (more on this bellow)
- [Django](https://www.djangoproject.com/): python web application framework.
- [Django Rest Framework](https://www.django-rest-framework.org/): library for developing REST APIs with Django.
- [React](https://reactjs.org/): javascript framework used on the frontend.
- [Postgres](https://www.postgresql.org/): database.
- [Dynaconf](https://www.dynaconf.com/): python settings library. Used to manage configurations.

Of this list, the most important one to understand for the purpose of backend development is Pulp, and the rest of this document will focus on that. For the rest of the technologies in the stack, please refer to their respective documentation.

## An overview of Pulp

Pulp is a pluggable library for managing software packages. It has the ability to store software (such as ansible collections and container images), sync them from remote sources (such as galaxy.ansible.com and quay.io) and organize them into repositories. We make use of the following pulp projects:

- [pulpcore](https://github.com/pulp/pulpcore/): by itself, this doesn't do a whole lot it provides the generic data structures required for storing any software type, which are added using plugins.
- [pulp_ansible](https://github.com/pulp/pulp_ansible/): this is a pulp plugin that adds support for ansible collections and roles. This is the primary plugin that galaxy_ng makes use of.
- [pulp_container](https://github.com/pulp/pulp_container/): another pulp plugin that adds support for container images. This is used for Execution Environment support in galaxy_ng.

Galaxy NG itself is just another pulp plugin, albeit a strange one. Rather than providing any content types of it's own, like all the other pulp plugins do, Galaxy NG integrates existing pulp plugins into a more cohesive Ansible user experience.

