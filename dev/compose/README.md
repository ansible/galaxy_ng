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

```

## Reload

Changing `.py` and `.yaml` files on any of the `DEV_SOURCE_PATH` directories will trigger reload of `api`, `worker`, and `content` services.


## Tips and Tricks.

**TBD**


### Debugging

### Connecting to Database

### Dumping and restoring the database

### Populating testing data
