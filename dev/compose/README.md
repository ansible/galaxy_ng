# Galaxy Simplified Compose Stack

Profiles:

- `standalone` - Run galaxy_ng for integration with Ansible Automation Platform

## Requirements

- `docker compose` version `>=2`

## Usage

Pick a profile as needed and on the root of `galaxy_ng` repository.

> Examples assumes `standalone` as the profile, change as needed.

Build images
```bash
docker compose -f dev/compose/standalone.yaml build
```

Run the stack
```bash
docker compose -f dev/compose/standalone.yaml up
# optionally pass `-d` to release the terminal
```

Exec commands on the `manager` service

Bash
```console
$ docker compose -f dev/compose/standalone.yaml exec manager /bin/bash
bash-4.4#
```
Django Admin
```console
$  docker compose -f dev/compose/standalone.yaml exec manager pulpcore-manager
Type 'pulpcore-manager help <subcommand>' for help on a specific subcommand.

Available subcommands:

[app]
    add-signing-service
    analyze-publication
...
```

Settings
```console
$ docker compose -f dev/compose/standalone.yaml exec manager dynaconf get DATABASES | python -m json.tool
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
$ docker compose -f dev/compose/standalone.yaml exec manager dynaconf list
CONTENT_ORIGIN<str> 'https://localhost'
CACHE_ENABLED<bool> False
CACHE_SETTINGS<dict> {'EXPIRES_TTL': 600}
ALLOWED_CONTENT_CHECKSUMS<list> ['sha224', 'sha256', 'sha384', 'sha512']
...
```

Stopping
```console
$ docker compose -f dev/compose/standalone.yaml down
# add -v to stop and remove volumes
```

> [!TIP]
> Stop with Ctrl + C if running without `-d` and then execute the `down` command.

## API Access

Galaxy API is available on:

[http://localhost:5001/api/galaxy/v3/swagger-ui/](http://localhost:5001/api/galaxy/v3/swagger-ui/)

AAP UI and API will be available only if started separately on:

[https://localhost](https://localhost)


## Running UI for standalone development

Ansible Hub UI can be started separately as a standalone `npm` run.

```console
# Assuming galaxy_ng is running on standalone compose.

$ git clone https://github.com/ansible/ansible-hub-ui ~/projects/ansible-hub-ui
$ git clone https://github.com/ansible/galaxy_ng ~/projects/galaxy_ng
```
Open 2 terminals:

On the first terminal:

```console
$ cd galaxy_ng
$ docker compose -f dev/compose/standalone.yaml up
```

On the second terminal:

```console
cd ansible-hub-ui
npm install
npm run start-standalone
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
$ docker compose -f dev/compose/standalone.yaml up --build
```

Optionally it can be informed in a single line:

```console
$ DEV_SOURCE_PATH="dynaconf:pulp_ansible:galaxy_ng" docker compose -f dev/compose/app.yaml up --build
```

> [!NOTE]
> if passing on the call line, remember to repass the same variable every time you interact with
>`docker compose` using the `run` command, usually `exec,logs,stats` doesn't require, but commands
> that starts the service container from scratch needs the variables.

Now when changes are detected on `.py` and `.yaml` files on any of the `DEV_SOURCE_PATH`
directories it will trigger reload of `api`, `worker`, and `content` services.

---

## LDAP Profile

To run the stack with API authentication via LDAP, use the following compose file:

```bash
docker compose -f dev/compose/ldap.yaml up
```

This configuration starts the stack with the LDAP backend enabled, allowing API authentication via LDAP.

---

### 1. Verify that the user exists

Run the following command to ensure that the user **fry** exists in the LDAP directory:

```bash
ldapsearch -x -H ldap://localhost:10389 -D "cn=admin,dc=planetexpress,dc=com" -w GoodNewsEveryone -b "ou=people,dc=planetexpress,dc=com" "(uid=fry)"
```

---

### 2. Generate the password hash

Replace `"user_new_password"` with your desired password and execute the command below to generate its hash:

```bash
docker exec -i compose-ldap-1 slappasswd -s "user_new_password"
```

This command will output the password hash. **Note down this hash**, as you will need it for the LDIF file.

---

### 3. Create the LDIF file for modifying the password

Create a file named, for example, `modify_password.ldif` with the following content. Replace `<password_hash>` with the hash obtained in the previous step:

```ldif
dn: cn=fry,ou=people,dc=planetexpress,dc=com
changetype: modify
replace: userPassword
userPassword: <password_hash>
```

---

### 4. Apply the modification to the LDAP server

Execute the following command to update the user's password on the LDAP server:

```bash
ldapmodify -x -H ldap://localhost:10389 -D "cn=admin,dc=planetexpress,dc=com" -w GoodNewsEveryone -f modify_password.ldif
```

After running this command, the password for the user **fry** will be updated with the new hash.

## Keycloak Profile

This guide explains how to set up and use the Keycloak authentication integration with the Galaxy NG development environment.

### Starting the Stack with Keycloak

To run the stack with API authentication via Keycloak, use the following compose file:

```bash
docker compose -f dev/compose/keycloak.yaml up
```

This configuration starts the Galaxy NG stack with Keycloak authentication backend enabled, allowing API authentication through Keycloak with LDAP user federation.

### Configuration Steps

#### 1. Initialize and Configure Keycloak

Once the Docker Compose stack is running, you need to configure Keycloak with the proper realm, client, and LDAP integration by running the provided Ansible playbook:

```bash
ansible-playbook keycloak-playbook.yaml
```

This playbook performs the following tasks:
- Creates the "aap" realm
- Sets up the "automation-hub" client
- Configures LDAP integration for user federation
- Creates necessary roles and mappers
- Gets the realm's public key

#### 2. Update the Galaxy NG Configuration

After running the playbook, copy the Keycloak realm public key from the output of the playbook and update the `PULP_SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY` environment variable in your configuration.

Example:
```bash
# Update the PULP_SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY in your environment
export PULP_SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY="MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA..."

# Restart the API service to apply the changes
docker compose -f dev/compose/keycloak.yaml restart api
```

### Managing LDAP Users

#### Modifying User Passwords in LDAP via Keycloak

To modify passwords for LDAP users:

1. Log in to the Keycloak admin console at http://localhost:8080/auth/ with:
   - Username: `admin`
   - Password: `admin`

2. Navigate to the "aap" realm.

3. Go to User Federation → LDAP.

4. Change the **Edit Mode** to "WRITABLE".

5. Click "Save".

6. Now you can edit LDAP users and their passwords directly from the Keycloak interface.

7. Alternatively, you can use the provided playbook in the `keycloak-utils` directory to change user passwords:
   ```bash
   ansible-playbook keycloak-utils/keycloak-change-user-password.yaml
   ```

### Testing the Authentication

To verify that the Keycloak authentication is working correctly, you can use either of the following methods:

#### Browser Authentication

You can navigate to http://localhost:5001/login/keycloak in your web browser. You will be redirected to the Keycloak login page where you can authenticate with your LDAP-federated user credentials.

#### API Testing with curl

Alternatively, you can verify the authentication flow programmatically using the following commands:

#### 1. Obtain an Access Token

```bash
TOKEN=$(curl -s -d 'client_id=automation-hub' \
        -d 'username=fry' \
        -d 'password=PlanetExpress2025!' \
        -d 'client_secret=REALLYWELLKEPTSECRET' \
        -d 'scope=openid' \
        -d 'grant_type=password' \
        "http://localhost:8080/auth/realms/aap/protocol/openid-connect/token" | jq -r '.access_token')
```

#### 2. Use the Token to Access a Protected API Endpoint

```bash
curl -v -L -X GET \
        -H "Authorization: Bearer $TOKEN" \
        "http://localhost:5001/api/_ui/v1/feature-flags/"
```

If the authentication is successful, you will receive the feature flags data from the API endpoint.

### Troubleshooting

#### User Authentication Issues

If users are unable to authenticate, check the following:

1. Verify the Keycloak client settings:
   - Ensure the client secret matches the one in the Galaxy NG configuration
   - Check that the redirect URIs are configured correctly

#### API Connection Issues

If the API cannot connect to Keycloak:

1. Verify the Keycloak public key is correctly set in the Galaxy NG environment.
2. Check the logs for the Galaxy NG API container:
   ```bash
   docker compose -f dev/compose/keycloak.yaml logs api
   ```
3. Ensure the Keycloak service is accessible from the API container.

### Reference LDAP Users

The following LDAP users are available in the default configuration:

- **fry** (Philip J. Fry)
- **leela** (Turanga Leela)
- **bender** (Bender Bending Rodriguez)
- **zoidberg** (Dr. John Zoidberg)

The password can be changed as described in the "Modifying User Passwords" section.


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

### LLB definition error

```bash
failed to solve: rpc error: code = Unknown desc = failed to solve with frontend dockerfile.v0: failed to create LLB definition: failed to do request: Head "http://localhost/v2/galaxy_ng/galaxy_ng/manifests/base": dial tcp [::1]:80: connect: connection refused
```

Solution

```bash
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0
```

## Tests

### Unit tests
Run unit tests with docker compose [Running unit tests](../../galaxy_ng//tests/unit/README.md)

### Integration tests
Run integration tests with docker compose, check the [Running integration tests](../../galaxy_ng/tests/integration/README.md)


## Tips and Tricks.

---

### Debugging

#### Step 1 - Add the breakpoint

Edit the file you want to debug and add a breakpoint

```python
__import__("ipdb").set_trace()
```

> [!TIP]
> Replace if you are using a different debugger, however the images has only **pdb** and **ipdb** installed.

If you discover other ways of debugging, like connecting dap protocol or vscode debugger, please update this file!

#### Step 2 - Now execute your stack or just the container you are trying to debug.

Example:

```bash
$ export DEV_SOURCE_PATH=galaxy_ng
$ docker compose -f dev/compose/standalone.yaml up migrations
# The container will keep running stopped on the breakpoint.
```

#### Step 3 - Attach

```bash
$ docker compose -f dev/compose/standalone.yaml attach migrations
ipdb>
```

> [!IMPORTANT]
> To detach from the container DO NOT use <kbd>Ctrl+c</kbd>,
> instead, use <kbd>Ctrl-p Ctrl-q</kbd>

---

**TBD**

### Connecting to Database

### Dumping and restoring the database

### Populating testing data
