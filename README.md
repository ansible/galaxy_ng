# Galaxy NG

[![Build Status](https://travis-ci.com/ansible/galaxy_ng.svg?branch=master)](https://travis-ci.com/ansible/galaxy_ng)

A Pulp plugin to support hosting your very own Ansible Galaxy.

This is a brand new take on Ansible Galaxy, so it will look and feel a bit different than the current [galaxy.ansible.com web site](https://galaxy.ansible.com). Over time we expect to migrate the web site to this code base, so for now you're looking into the future, and you have an opportunity to help shape that future.

Our mission is to help organizations share Ansible automation and promote a culture of collaboration around Ansible automation development. We'll be providing features that make it easy to create, discover, use and distribute Ansible automation content.

For more information, please see the [documentation](docs/index.rst) or the [Pulp project page](https://pulpproject.org/).

## OpenAPI Spec

View the latest version of the spec by [clicking here](https://petstore.swagger.io/?url=https://raw.githubusercontent.com/ansible/galaxy_ng/master/openapi/openapi.yaml).

### Creating your development environment

#### 1. Build docker image

```console
$ ./compose build
```

#### 2. Start database and redis services

```console
$ ./compose up -d postgres redis
```

#### 3. Run migrations

```console
$ ./compose run --rm api manage migrate
```

#### 4. Import initial data (via fixture)

```console
$ ./compose run --rm -e PULP_FIXTURE_DIRS='["/app/dev/automation-hub"]' \
>     api manage loaddata initial_data.json
```

#### 5. Import initial data (manually)

5.1. Create superuser.

Default username and password used for development environment is `admin` \ `admin`.

```console
$ ./compose run --rm api manage createsuperuser
```

Example output:

```text
Username: admin
Email address: admin@example.com
Password:
Password (again):
The password is too similar to the username.
This password is too short. It must contain at least 8 characters.
This password is too common.
Bypass password validation and create user anyway? [y/N]: y
Superuser created successfully.
```

5.2. Create `pulp_ansible` repository and distribution

Open Django shell.

```console
$ ./compose run --rm api manage shell
````

Execute the following code:

```python console
>>> from pulp_ansible.app.models import AnsibleRepository, AnsibleDistribution
>>> repo = AnsibleRepository.objects.create(name='automation-hub')
>>> AnsibleDistribution.objects.create(name='automation-hub', base_path='automation-hub', repository=repo)
<AnsibleDistribution: automation-hub>
>>> # Press <CTRL+D> to exit.
```

#### 6. Start services

In background:

```console
$ ./compose up -d
```

In foreground:

```console
$ ./compose up
```

### Additional development adjustments

- Assign user to the `system:partner-engineers` group:

through Django shell (`./compose run --rm api manage shell`), use the following commands

```python console
>>> from galaxy_ng.app.models.auth import User, Group
>>> user = User.objects.get(username="ansible-insights")
>>> pe_group = Group.objects.get(name="system:partner-engineers")
>>> user.groups.add(pe_group)
>>> user.save()
```
