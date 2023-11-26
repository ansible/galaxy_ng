# Community Development Stack

## The architecture

As noted in the overview, GalaxyNG is considered a [pulp plugin](https://docs.pulpproject.org/pulpcore/plugins/index.html). As opposed to more vanilla django application, pulp plugins are extensions to the pulpcore django application. Most of the plugin application code is extending or making use of pulp's underlying primitives such as "distributions", "repositories" and "content".

Governance of the various projects has increasingly leaned towards writing less code in the galaxy_ng repository and more in the pulp_ansible repository. The code in the pulp_ansible repository is sufficiently generic to be usable for not only GalaxyNG but also as components in the Red Hat Satellite product. GalaxyNG is slowly turning into more of an "integration project" than a project with unique features. This pattern of where to write code has slightly diverged in the case of the api/v1 codebase because of differences in pulp_ansible's implementation that are incompatible with many of the roles indexed by [galaxy](https://galaxy.ansible.com).

As a hopeful contributor, you may need to first figure out where to write code for a new feature or a bugfix. General guidance is to start any new enhancements for api/v3 in the pulp_ansible project. Anything for api/v1 is in the galaxy_ng project. If you aren't sure or can't figure out where the code should be, please reach out on the IRC channels and we'll help guide you.


### Services

* api server
* worker(s)
* content app
* postgres


### Related Projects

* https://github.com/ansible/galaxy_ng
* https://github.com/ansible/ansible-hub-ui
* https://github.com/pulp/pulp_ansible
* https://github.com/pulp/pulp_container
* https://github.com/pulp/pulpcore


### api/v1

Found in https://github.com/ansible/galaxy_ng/tree/master/galaxy_ng/app/api/v1

The v1 api was re-implemented in GalaxyNG from scratch as simple django models, views, serializers and filtersets. This api version allows for role imports and indexing from [github](https://github.com) in the same conceptual way that roles were handled in [galaxy](https://galaxy.ansible.com). Two models comprise most of how api/v1 works under the covers: "LegacyRole" and "LegacyNamespace".

Access control in api/v1 is controlled by a model we have termed a "Legacy Namespace". These differ from the namespaces found in api/v3 because of naming restrictions there which aren't suitable for many of the usernames that have been created on [galaxy](https://galaxy.ansible.com). Each legacy namespace has a list of "owners", or github usernames that have control over the namespace to add/remove owners, upload new roles, delete roles, etc. The social auth handler will automatically create a legacy namespace and set the owner for logged in users if one does not already exist.


### api/v3

Found in https://github.com/ansible/galaxy_ng/tree/master/galaxy_ng/app/api/v3

The v3 api is 100% focused on collections and collection namespaces. As time progresses, the v3 api becomes more and more a redirect to endpoints provided by pulp_ansible. 

Access control over collections is controlled by the v3 collection namespaces and pulp object level RBAC. Users are added to a group and the group is bound to the namespace with a permission. For the community instances, the group and permission bindings are handled automatically by the social auth handler.

### OCI Env

The community profile is only supported via the [oci-env](https://github.com/pulp/oci_env) project. The "old" dev stack that utilizes the "compose" script in the project root is no longer supported and will be removed in the near future.

To get started, it's recommended to a create a new top level directory to store your various checkouts.

```bash
/src
`- oci_env
`- galaxy_ng
`- ansible-hub-ui
```

Clone the three projects into the src dir.
```bash
cd src
git clone https://github.com/pulp/oci_env
git clone https://github.com/ansible/galaxy_ng
git clone https://github.com/ansible/ansible-hub-ui
```

Create a virtual env in the src dir
```bash
cd src
python -m venv venv
```

Install the oci-env client
```bash
cd src
source venv/bin/activate
cd oci_env
pip install -e client
```

Start the stack build and spinup
```bash
cd src/galaxy_ng
make oci/community
```

You can now reach the api at http://localhost:5001. The makefile targets created a couple test users, namely admin:admin for the primary superuser. This is purely an API stack with no UI. That makes it difficult to test and use github users, so see the next section about adding the UI.

### React.js UI

To connect to the UI, the default address is http://localhost:8002. If social auth is enabled, you'll be forced to auth via Github if clicking on the "login" link at the top right of the page. The presence of `SOCIAL_AUTH_GITHUB_KEY` & `SOCIAL_AUTH_GITHUB_SECRET` in the backend configuration triggers dynaconf to set a feature flag for external auth that the UI reads and alters the login link accordingly. If you want to bypass github and use a local django user, go directly to the http://localhost:8002/ui/login url and login that way.

#### starting directly

For development work on the UI, it's easiest to launch the webpack dev server outside the compose stack. The npm start scripts and configuration will have it redirect api calls to http://localhost:5001 by default, so no hacking is necessary to make it work locally.

1. Install [NVM](https://github.com/nvm-sh/nvm) to easily manage node.js versions.
2. Use NVM to install and set the version to 18: `nvm install 18`,
3. Clone the [ansible-hub-ui](https://github.com/ansible/ansible-hub-ui) repo to the desired location.
4. From the checkout, run `npm install`.
5. From the checkout, run `npm run start-community`.

### Configuration

The galaxy_ng project is a highly configurable application, but only at startup time. Almost all of the behavior of the application is influenced by environment variables and static settings.py files that are read in by [django](https://www.djangoproject.com/) and [dynaconf](https://www.dynaconf.com/). None of these settings live in the database currently, so they can only be declared before the application starts. If you change anything after starting the stack, it is recommeneded to completely destroy the stack, wipe all your docker images and spin up from scatch.

The community specific settings are found in `galaxy_ng/profiles/community/pulp_config.env`

1. Comment out the `SOCIAL_AUTH_GITHUB_BASE_URL` line
2. Add `PULP_SOCIAL_AUTH_GITHUB_KEY=<value>`
3. Add `PULP_SOCIAL_AUTH_GITHUB_SECRET=<value>`

The github key and secret are provided by configuring an oauth account on github.com under your user's developer settings. The oauth application config needs to have a valid and resolvable homepage url and the callback url should be the same host with "/complete/github/" as the path. For local testing, you can use http://localhost:8002 as base url.

## Testing

The GalaxyNG project is a "test driven development" (TDD) project. Our interpretation of TDD is that -every- PR to the master branch -must- have some sort of test or test changes. It can be unit, functional or integration, but something must be written. It doesn't matter if the PR is a bugfix or a feature, tests must be written. This is how we avoid regressions and keep track of how new code is meant to work inside a very complex and spread out architecture with many different configurable behaviors.

### Unit

More focus has been spent on the integration tests, but there are a few unit tests in the project. The compose stack must be running to launch unit tests, as they are using django and postgres with a temporary database to do real SQL calls that are incompatible with sqlite.

To launch units, execute `make docker/test/unit`. Specific tests can be selected by running `TEST=xyz make docker/test/unit`.

### Functional

Pulp has a testing concept known as [functional tests](https://docs.pulpproject.org/pulpcore/en/master/nightly/contributing/tests.html#functional-tests). These are mostly using a suite of fixtures, auto-generated api clients and strict style to do integration testing. The environment needed to run functional tests is somewhat complicated to setup, so the GalaxyNG project instead writes integration tests. However, if you end up writing patches for any of the repositories in https://github.com/pulp, you will be required to write functional tests.


### Integration

The GalaxyNG project backs the Red Hat product named "Automation HUB". As it is a product, it has a formal QE team testing release features with their own private internal frameworks built around pytest. We decided to "shift left" on integration testing and put it on developers to write integration tests along with their pullrequests (TDD). The initial batch of integration tests came from forking the internal tests and pulling out elements of the testing framework that were either too complicated or reliant on systems behind the corporate firewall. Since that time, the tests have grown substantially and comprise a much larger level of coverage. The integration tests aim to be as simple as possible to run and "framework light" in the sense that you really only need pytest, python-requests and ansible-core. Most integration tests are instantiating a REST api client that then talks to the api and asserts certain behaviors such as return codes, response types/shape and errors.

Each docker-compose profile has it's own `RUN_INTEGRATION.sh` file in the `dev/<profile>/` directory that sets necessary variables and pytest marks suitable for that environment. The community script `dev/standalone-community/RUN_INTEGRATION.sh` is mostly just setting the `-m community` argument for pytest so that it only runs the tests that have been [marked](https://docs.pytest.org/en/7.1.x/how-to/mark.html) as such. Once you have the stack running with the appropriate config, you can execute ./dev/standalone-community/RUN_INTEGRATION.sh to launch the tests. Specific test are easiest to call by appending -k "<testname>" to the command.

If you write a new test specific to the community profile, please add a `@pytest.mark.community` decorator to the test function. Currently, all community related test are in https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/tests/integration/api/test_community.py and https://github.com/ansible/galaxy_ng/blob/master/galaxy_ng/tests/integration/cli/test_community.py. Other files can be added as needed as long as they have a suitable filename and the relevant pytest marks.


## Commits

We have strict checks on commit messages to ensure proper reference to https://issues.redhat.com and that all are cryptographically signed. Creating a gpg signing key for git and configuring github to use it is beyond the scope of this document, but the end result is that you should be able to start your commits by running:

```bash
git commit -s -S
```

The message needs to be in the format:

```
<Short commit title>

<Longer commit description and notes>

Issue: AAH-XXX

Signed-off-by: First Last <email@domain>
```

If you are working on a bug or feature not tracked in a jira ticket, it's fine to use "No-Issue" instead of "Issue: AAH-XXX". If you are working on a jira ticket, you will need to create a suitable changelog file in [CHANGES](https://github.com/ansible/galaxy_ng/tree/master/CHANGES) folder.
