# Community Development Stack

## The architecture

As noted in the overview, GalaxyNG is considered a [pulp plugin](https://docs.pulpproject.org/pulpcore/plugins/index.html). As opposed to more vanilla django application, pulp plugins are extensions to the pulpcore django application. Most of the plugin application code is extending or making use of pulp's underlying primitives such as "distributions", "repositories" and "content".

Governance of the various projects has increasingly leaned towards writing less code in the galaxy_ng repository and more in the pulp_ansible repository. The code in the pulp_ansible repository is sufficiently generic to be usable for not only GalaxyNG but also as components in the Red Hat Satellite product. GalxyNG is slowly turning into more of an "integration project" than a project with unique features. This pattern of where to write code has slightly diverged in the case of the api/v1 codebase because of differences in pulp_ansible's implementation that are incompatible with many of the roles indexed by [galaxy](https://galaxy.ansible.com).

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

Access control in api/v1 is controlled by a model we have termed a "Legacy Namespace". These differ from the namespacs found in api/v3 because of naming restrictions there which aren't suitable for many of the usernames that have been created on [galaxy](https://galaxy.ansible.com). Each legacy namespace has a list of "owners", or github usernames that have control over the namespace to add/remove owners, upload new roles, delete roles, etc. The social auth handler will automatically create a legacy namespace and set the owner for logged in users if one does not already exist.


### api/v3

Found in https://github.com/ansible/galaxy_ng/tree/master/galaxy_ng/app/api/v3

The v3 api is 100% focused on collections and collection namespaces. As time progresses, the v3 api becomes more and more a redirect to endpoints provided by pulp_ansible. 

Access control over collections is controlled by the v3 collection namespaces and pulp object level RBAC. Users are added to a group and the group is bound to the namespace with a permission. For the community instances, the group and permission bindings are handled automatically by the social auth handler.

## Docker compose

For development work on the galaxy_ng project or when integration testing a pulp_ansible+galaxy_ng feature, docker-compose is the preferred pathway. With all the moving parts in the stack, docker-compose is the simplest way to spin up a functional dev environment.

!!! warning
    docker-compose 2.x (the golang rewrite) has compatibility issues with our current stack, so please use the 1.x version that was written in python.

### Profiles & Configuration

The galaxy_ng project is a highly configurable application, but only at startup time. Almost all of the behavior of the application is influenced by environment variables and static settings.py files that are read in by [django](https://www.djangoproject.com/) and [dynaconf](https://www.dynaconf.com/). None of these settings live in the database currently, so they can only be declared before the application starts.

The "community" profile of galaxy_ng is a combination of settings driven by the docker-compose files found in [the standalone-community directory](https://github.com/ansible/galaxy_ng/tree/master/dev/standalone-community). To get his profile to run, you must do a few things:

1. Copy the ".compose.env.example" file at the root of the repository to a new file named ".compose.env".
2. Change the COMPOSE_PROFILE value in ".compose.env" from "standalone" to "standalone-community".
3. Add SOCIAL_AUTH_GITHUB_KEY=<value> to the bottom of ".compose.env".
4. Add SOCIAL_AUTH_GITHUB_SECRET=<value> to the bottom of ".compose.env".
5. Add SOCIAL_AUTH_LOGIN_REDIRECT_URL = "/" to the bottom of galaxy_ng/app/settings.py
6. Add SOCIAL_AUTH_REDIRECT_IS_HTTPS = True to the bottom of galaxy_ng/app/settings.py if your stack will be behind an http server with SSL enabled.

The github key and secret are provided by configuring an oauth account on github.com under your user's developer settings. The oauth application config needs to have a valid+resolvable homepage url and the callback url should be the same host with "/complete/github/" as the path. For local testing, you can use something like http://localhost:8002 as the host.

Afterwards, the stack can be created and spun up via:

1. make docker/all
2. ./compose up


You can how reach the api at http://localhost:5001. The makefile targets created a couple test users, namely admin:admin for the primary superuser. This is purely an API stack with no UI. That makes it difficult to test and use github users, so see the next section about adding the UI.


### The UI

To connect to UI, the default address is http://localhost:8002. If social auth is enabled, you'll be forced to auth via github if clicking on the "login" link at the top right of the page. The presence of SOCIAL_AUTH_GITHUB_KEY & SOCIAL_AUTH_GITHUB_SECRET in the backend configuration triggers dynaconf to set a feature flag for external auth that the UI reads and alters the login link accordingly.

If you want to bypass that and use a local django user, go directly to the http://localhost:8002/ui/login url and login that way.

#### docker-compose
Inside .compose.env, you'll find a commented out line referencing ANSIBLE_HUB_UI_PATH. If you want to add a UI to the compose stack, this needs to be uncommented and set to a valid absolute path for a checkout of [ansible-hub-ui](https://github.com/ansible/ansible-hub-ui). The compose spinup should properly allocate an alpine container with the appropriate node.js version and install+build+launch the UI.

#### starting directly

For development work on the UI, it's easier to launch the webpack dev server outside the compose stack. The npm start scripts and configuration will have it redirect api calls to http://localhost:5001 by default, so no hacking is necessary to make it work locally.

1. Install [NVM](https://github.com/nvm-sh/nvm)
2. Use NVM to install and set the version to 16. "nvm install 16"
3. Clone the [ansible-hub-ui](https://github.com/ansible/ansible-hub-ui) repo to the desired location.
4. From the checkout, run "npm install"
5. From the checkout, run "npm run start-community"
