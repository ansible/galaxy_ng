# Galaxy Simplified Compose Stack

Profiles:

- `aap` - Run galaxy_ng for integration with Ansible Automation Platform and Resource Server
- `community` - Run galaxy_ng for galaxy.ansible.com development
- `cloud` - Run galaxy_ng for console.redhat.com development

## Requirements

- `docker compose` version `>=2`

## Usage

Pick a profile as needed and on the root of `galaxy_ng` repository.

> Examples assumes `aap` as the profile, change as needed.

Build images
```bash
docker compose -f dev/compose/aap.yaml build
```

Run the stack
```bash
docker compose -f dev/compose/aap.yaml up
# optionally pass `-d` to release the terminal
```

Exec commands on the `manager` service

Bash
```console
$ docker compose -f dev/compose/aap.yaml exec manager /bin/bash
bash-4.4#
```
Django Admin
```console
$  docker compose -f dev/compose/aap.yaml exec manager pulpcore-manager
Type 'pulpcore-manager help <subcommand>' for help on a specific subcommand.

Available subcommands:

[app]
    add-signing-service
    analyze-publication
...
```

Settings
```console
$ docker compose -f dev/compose/aap.yaml exec manager dynaconf get DATABASES | python -m json.tool
{
  "default": {
    "ENGINE": "django.db.backends.postgresql",
    "HOST": "postgres",
    "NAME": "galaxy_ng",
    "PASSWORD": "galaxy_ng",
    "PORT": 5432,
    "USER": "galaxy_ng"
  }
}
```
```console
$ docker compose -f dev/compose/aap.yaml exec manager dynaconf list
CONTENT_ORIGIN<str> 'https://localhost'
CACHE_ENABLED<bool> False
CACHE_SETTINGS<dict> {'EXPIRES_TTL': 600}
ALLOWED_CONTENT_CHECKSUMS<list> ['sha224', 'sha256', 'sha384', 'sha512']
...
```

Stopping
```console
$ docker compose -f dev/compose/aap.yaml down
# add -v to stop and remove volumes
```


## API Access

Galaxy API is available on:

[http://localhost:5001/api/galaxy/v3/swagger-ui/](http://localhost:5001/api/galaxy/v3/swagger-ui/)

AAP UI and API will be available only if started separately on:

[https://localhost](https://localhost)

Ansible Hub UI can be started separately as a standalone `npm` run.


```console
# Assuming galaxy_ng is running on community compose.

$ git clone https://github.com/ansible/ansible-hub-ui ~/projects/ansible-hub-ui
$ git clone https://github.com/ansible/galaxy_ng ~/projects/galaxy_ng
```
Open 2 terminals:

On the first terminal:

```console
$ cd galaxy_ng
$ docker compose -f dev/compose/community.yaml up
```

On the second terminal:

```console
cd ansible-hub-ui
npm install
API_PROXY_PORT=5001 API_BASE_PATH=/api/galaxy/ npm run start-standalone
```

UI will be available on http://localhost:8002 and API on http://localhost:5001


## Auto Reload and Local Checkouts

To have the services `api`, `worker` and `content` to automatically reload when
source code changes it is required to set which paths the `reloader` must watch for changes.

Set the variable `DEV_SOURCE_PATH` with the packages you want to add to the reloader list.

Those repositories must be local checkouts located on the same level of the `galaxy_ng` repository.

Example:

Get the repositories locally in the same root path.
```console
$ git clone https://github.com/dynaconf/dynaconf  ~/projects/dynaconf
$ git clone https://github.com/pulp/pulp_ansible ~/projects/pulp_ansible
$ git clone https://github.com/ansible/galaxy_ng ~/projects/galaxy_ng
```

> **IMPORTANT** Ensure all the repos are checked out to compatible branches.
> for example. you may be on galaxy_ng:master and reading `setup.py` you
> see that it requires `pulp_ansible>2.10,<3` then ensure you checkout `pulp_ansible`
> to a compatible branch.

Start the compose setting the desired editable paths.

```console
$ cd ~/projects/galaxy_ng
$ export DEV_SOURCE_PATH="dynaconf:pulp_ansible:galaxy_ng"
$ docker compose -f dev/compose/app.yaml up --build
```

Optionally it can be informed in a single line:

```console
$ DEV_SOURCE_PATH="dynaconf:pulp_ansible:galaxy_ng" docker compose -f dev/compose/app.yaml up --build
```

> **NOTE** if passing on the call line, remember to repass the same variable every time you interact with
>`docker compose` for exec, logs, down etc.

Now when changes are detected on `.py` and `.yaml` files on any of the `DEV_SOURCE_PATH`
directories it will trigger reload of `api`, `worker`, and `content` services.


## Troubleshooting

### VersionConflict error

Example:
```bash
api-1         |    raise VersionConflict(dist, req).with_context(dependent_req)
api-1         | pkg_resources.VersionConflict: (pkg_foo 3.2.6 (/venv/lib/python3.11/site-packages), Requirement.parse('pkg_foo<3.1.13,>=3.1.12'))
```

Solution 1:
Clean up local build files:

```bash
cd ~/projects/galaxy_ng
rm -rf .eggs
rm -rf build
rm -rf galaxy_ng.egg-info
```

Solution 2:

- Ensure `LOCK_REQUIREMENTS` is set to `0`
- Ensure all your local checkouts are checked out to compatible branches


## Tips and Tricks.

**TBD**

### Debugging

### Connecting to Database

### Dumping and restoring the database

### Populating testing data
