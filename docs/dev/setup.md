# Development Setup

## The Project Repository

1. Create your own fork of the repository
2. Clone it to your projects folder

```bash
cd your/preferred/projects/folder
git clone git@github.com:<YOUR_USER_NAME>/galaxy_ng.git
```

!!! important
    We require all commits to be signed, so configure PGP signing on your git


## Configuring your local code editor

Set your working directory to Galaxy folder

```bash
cd galaxy_ng
```

You can use your editor of choice and if you want to have the editor (ex: VsCode) to inspect
the code for you might need to create a virtual environment and install the packages.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r dev_requirements.txt
python -m pip install -r docs_requirements.txt
python -m pip install -r integration_requirements.txt
python -m pip install -e .
```

Now you can for example open `code .` and have VsCode to find the libraries you need.

## Running the container based dev environment


Our containerized development environment configuration is loaded from
the `.compose.env` script. You'll first need to configure it, and the
easiest way to do that is by copying an example script
`.compose.env.example`:


```bash
cp .compose.env.example .compose.env
```

By default, the development environment is configured to run in
*insights* mode, which requires a 3rd party authentication provider. If
you're working outside of the Red Hat cloud platform, you'll want to
switch it to *standalone* mode by modifying your `.compose.env` file,
and setting the `COMPOSE_PROFILE` variable to `standalone`, as shown in
the following example:

```env
COMPOSE_PROFILE=standalone
```

If you want to run in standalone mode while using Keycloak to provide
single sign-on with a
`pre-populated LDAP server <https://github.com/rroemhild/docker-test-openldap>`\_
you'll want to switch it to *standalone-keycloak* mode by modifying your
`.compose.env` file, and setting the `COMPOSE_PROFILE` variable to
`standalone-keycloak`, as shown in the following example:

```env
COMPOSE_PROFILE=standalone-keycloak
```

## Enable the UI

If you would like to develop using the UI, simply do the following:

1.  Clone https://github.com/ansible/ansible-hub-ui to the same path where `galaxy_ng` is located.
    ```bash
    cd your/preferred/projects/folder
    git clone https://github.com/ansible/ansible-hub-ui
    cd galaxy_ng
    ```

2.  Set `ANSIBLE_HUB_UI_PATH` in your `.compose.env` file to point to
    the location of the cloned UI repo. Absolute paths aren't required,
    but they're easier to set up. If you want to use a relative path, it
    has to be relative to `dev/docker-compose.yml`

    ```bash
    ANSIBLE_HUB_UI_PATH='/your/preferred/projects/folder/ansible-hub-ui'
    ```

3.  Complete the rest of the steps in the next section. Once everything
    is running the UI can be accessed at http://localhost:8002



???  "Access the UI in insights mode"

    Skip this step if you don't have access to the Red Hat VPN.

    If you want to be able to run the app in insights mode you need to add
    the following in your `/etc/hosts` file.

    ```bash
    127.0.0.1 prod.foo.redhat.com 
    127.0.0.1 stage.foo.redhat.com 
    127.0.0.1 qa.foo.redhat.com 
    127.0.0.1 ci.foo.redhat.com
    ```

    To access the UI when running in insights mode:

    1.  Connect to the Red Hat VPN

    2.  Navigate to
        https://ci.foo.redhat.com:1337/beta/ansible/automation-hub

    3.  You'll need a Red Hat username and password to authenticate with the
        dev Red Hat SSO server. Anyone on the Galaxy team should be able to
        provide you with one.

## Run the Build Steps

Next, run the following steps to build your local development
environment:


1. Build the docker image

    ```bash
    make docker/build
    ```

2. Initialize and migrate the database

    ```bash
    make docker/migrate
    ```

3. Load dev data

    ```bash
    make docker/loaddata 
    make docker/loadtoken
    ```


!!! tip
    You can run everything at once with 
    ```bash
    make docker/build docker/migrate docker/loaddata docker/loadtoken
    ```


**Start the services**

In foreground keeping terminal opened for watching outputs
```bash
./compose up
```

In Background (you can close the terminal later)
```bash
./compose up -d
```

## Keycloak

??? tip "Using Keycloak"

    If using `standalone-keycloak` you will need to initialize your Keycloak
    instance before running migrations and starting the remaining services.

    1.  Start the Keycloak instance and dependencies

        ```bash
        ./compose up -d keycloak kc-postgres ldap
        ```

    2.  Bootstrap the Keycloak instance with a Realm and Client then capture
        the needed public key

        ```bash
        ansible-playbook ./dev/standalone-keycloak/keycloak-playbook.yaml
        ```
        > **NOTE** Try again if it fails at the first run, services might not be
        available yet.

    3.  Update your `.compose.env` file with the public key found at the end
        of the playbook run

        ```bash
        PULP_SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY="keycloak-public-key"
        ```

    After the standard development set up steps, when you access
    http://localhost:8002 it will redirect to a Keycloak Open ID Connect
    flow login page, where you can login with one of the development SSO
    user's credentials (the password is the username). If you want to login
    with non-Keycloak users, you need to use the
    `Django admin console <http://localhost:5001/automation-hub/admin/>`\_.

    If you want to login as a superuser, you can do one of two things:

    1.  Login to the
        `Django admin console <http://localhost:5001/automation-hub/admin/>`\_
        with the admin user

    2.  Login to the `Keycloak instance <http://localhost:8080/>`\_ with
        admin/admin to edit the LDAP user's roles: Choose a development SSO
        user, select Role Mappings \> Client Roles \> automation-hub and add
        the `hubadmin` role. A user is associated with the appropriate
        group(s) using the user\_group pipeline.


## Testing data

??? tip "Push Container Images to local registry"

    !!! info
        ```
        make api/push-test-images
        ```
        will push a bunch of testing images to your running system

    To push images into the container image registry hosted by galaxy\_ng
    (via pulp\_container), you need to tag an image first to tell Docker or
    Podman that you want to associate the image with the registry. On a
    local development setup, the pulp\_container runs along with the Galaxy
    API on port 5001.

    Tag an image like this:

        docker image tag <IMAGE_ID> localhost:5001/<NAME>:<VERSION>

    or, to associate with a namespace:

        docker image tag <IMAGE_ID> localhost:5001/<NAMESPACE>/<NAME>:<VERSION>

    And then push the image and the engine will upload it to the
    now-associated registry:

        docker push localhost:5001/testflat

??? tip "Creating a set of collections for testing"
    
    !!! info
    ```
    make api/create-test-collections
    ```
    Will generate collections and populate the system


## Additional Dependencies

When running docker environment, the project's parent directory is
mounted into container as `/app`. All projects listed in
`DEV_SOURCE_PATH` environment variable are installed in editable mode
(`pip install -e`) in the container. To load additional projects such as
`galaxy-importer` or `pulp_ansible` into the container from host file
system you should clone them into the parent directory relative to your
`galaxy_ng` working copy location.

For example you want to work on `galaxy-importer` project and run
development environment with your changes made locally. Assuming your
current working directory is `galaxy_ng`.

1.  Clone `galaxy-importer` to parent directory::

        $ git clone https://github.com/ansible/galaxy-importer.git ../galaxy-importer

2.  Add `galaxy-importer` to `DEV_SOURCE_PATH` variable in your
    `.compose.env` file::

        export DEV_SOURCE_PATH='galaxy_ng:galaxy-importer'

3.  Recreate your development environment::

        ./compose down 
        make docker/build docker/migrate
        ./compose up


!!! tip
    The step above can be done for other Pulp plugins such as `pulp_ansible` or `pulp_container`


## Steps to run dev environment with specific upstream branch

1.  **Clone** locally `galaxy_ng`, `pulpcore` and `pulp_ansible` all the
    repos must be located at the same directory level.

        cd ~/projects/
        git clone https://github.com/pulp/pulpcore
        git clone https://github.com/pulp/pulp_ansible
        git clone https://github.com/ansible/galaxy_ng
        # and optionally
        git clone https://github.com/ansible/ansible-hub-ui
        git clone https://github.com/ansible/galaxy_importer

2.  **Checkout to desired branches.** `pulp_ansible` master is
    compatible with a specific range of `pulpcore` versions. So the
    recommended is to checkout to specific branch or tag following the
    contraints defined on pulp\_ansible/requirements.txt or leave it
    checked out to master if you know it is compatible with the
    pulp\_ansible branch you have. Example:

        cd ~/projects/pulpcore
        git checkout 3.9.0

    This is also possible to checkout to specific pull-requests by its
    `refs/pull/id`.

3.  Edit the `galaxy_ng/.compose.env` file.

        cd ~/projects/galaxy_ng
        cat .compose.env

        COMPOSE_PROFILE=standalone
        DEV_SOURCE_PATH='pulpcore:pulp_ansible:galaxy_ng'
        LOCK_REQUIREMENTS=0

    **DEV\_SOURCE\_PATH** refers to the repositories you cloned locally,
    the order is important from the highest to the low dependecy,
    otherwise pip will raise version conflicts.

    So **pulpcore** is a dependency to **pulp\_ansible** which is a
    dependency to **galaxy\_ng**, this order must be respected on
    **DEV\_SOURCE\_PATH** variable.

    **LOCK\_REQUIREMENTS** when set to 0 it tells docker to bypass the
    install of pinned requirements and rely only on packages defined on
    `setup.py` for each repo.

4.  Run `./compose build` to make those changes effective.

5.  Run desired compose command: `./compose up`, `./compose run` etc...

## Bumping The Version

The canonical source of truth for the 'version' is now in setup.cfg in
the `bumpversion` stanza:

```ini
[bumpversion]
current_version = 4.3.0.dev
```

To update version, it is recommended to "bump" the version instead of
explicitly specifying it.

Use bump2version to increment the 'version' string wherever it is
needed.

It can 'bump' the 'patch', 'minor', 'major' version components.

There are also Makefile targets for bumping versions. To do a 'patch'
version bump, for example:

     $ make dev/bumpversion-patch

The above command will rev the 'patch' level and update all the files
that use it.

Note: Currently, the bump2version config does not git commit or git tag
the changes. So after bumping the version, you need to commit the
changes and tag manually.

       $ git commit -v -a
       $ git tag $NEWVERSION

bump2version can also do this automatically if we want to enable it.

## Debugging


https://github.com/ansible/galaxy\_ng/wiki/Debugging-with-PDB

## Add galaxy-importer.cfg to dev environment


To set your own galaxy-importer.cfg, add something like this to
`/dev/Dockerfile.base`:

    RUN mkdir /etc/galaxy-importer \
        && printf "[galaxy-importer]\n \
    REQUIRE_V1_OR_GREATER = True\n \
    LOG_LEVEL_MAIN = INFO\n" | tee /etc/galaxy-importer/galaxy-importer.cfg


## Documentation


Docs are writen using [mkdocs](https://squidfunk.github.io/mkdocs-material/reference/#usage)

- Markdown files under `/docs` folder are documentation pages.
- Menu is set on `mkdocs.yml` file.

After the edits to the docs are done you can run

```
make docs/install
make docs/serve
``` 

Then you can open http://localhost:8000 and see your live reloading changes to the docs markdown files.