# Community User Guide

## API 

If you are looking for v3 API reference please go to [API v3](api_v3.md)

## Servers

We have multiple instances of the beta site running to cover the dev, staging and production lifecycle.

1. https://beta-galaxy.ansible.com/
2. https://beta-galaxy-stage.ansible.com/
3. https://beta-galaxy-dev.ansible.com/

The "dev" instance is auto-deployed from new commits to the master branch of https://github.com/ansible/galaxy_ng. Staging and Production deployments are triggered manually or via new tags on the git repository.

All instances are wired up for github social auth, so you can log into any of them with your github account.

## Logging in

Visit https://beta-galaxy.ansible.com/ in any modern web browser. Once the site loads, click on the "login" link
at the top right of the page. On your first attempt, you'll be brought to a github authorization page. This is
to be expected because github social auth is the default and only supported login mechanism in https://galaxy.ansible.com and for the future replacement. Once authorized, you should be redirected back to the main page and see your github username replace the word "login" at the top right of the page.


## Generating an API token

The UI path for GalaxyNG to retrieve an api token differs from Galaxy. In the left hand nav menu, click on "Collections" > "Api token management". Click the blue "Load Token" button to reveal your API token.


!!! info
    Each time you click on "Load Token", it will invalidate the old token and make a new one. Be sure to save
    your token somewhere safe and secure and not rely on the token management page to keep track of it for you. 


## Ansible Core CLI setup

The ansible-galaxy cli is configured by default to talk to https://galaxy.ansible.com. To configure ansible core to talk 
to the beta galaxy_ng server, create an ansible.cfg file with the following content.

```ini
[galaxy]
server_list = beta

[galaxy_server.beta]
url = https://beta-galaxy.ansible.com/api/
token = <your-api-token>
```

!!! important
    You only need a token set in the config if you plan on importing or uploading content. Anonymous
    read-only operations are fully supported.

## Finding Roles

Standalone roles are searchable via the UI, api or galaxy cli.

### UI
In the left nav menu, click on "Legacy" and then "Legacy Roles". Once the legacy roles page loads, a filter tool
will be present at the top of the page. Search options are keywords or tags. Tags come from the role's metadata file
and are defined the role author. Keywords are a full text search across the role's namespace, name and description.

### API

The v1 rest api has filter parameter support similar to the current code on https://galaxy.ansible.com.

```bash
# Find all roles created by a specific github user.
curl 'https://beta-galaxy.ansible.com/api/v1/roles/?github_user=geerlingguy'

# Find all roles containing a keyword in the namespace, name or description.
curl 'https://beta-galaxy.ansible.com/api/v1/roles/?keyword=docker'
```

### CLI

The ansible-galaxy CLI also supports role search

```bash
ansible-galaxy role search --help
```


## Finding Collections
Collections do have search support in the UI.

1. In the left-nav click "Collections".
2. Choose keywords or tag.
3. Type the term or select a tag to filter the list of results.

Future support for collection search in the ansible-galaxy CLI is [TBD](https://issues.redhat.com/browse/AAH-1968).


## Installing Roles

Role installs should work as they did before with https://galaxy.ansible.com

`ansible-galaxy role install geerlingguy.docker`


## Installing Collections

Collection installs should work as they did before with https://galaxy.ansible.com

`ansible-galaxy collection install community.general`


## Importing Roles

Role imports are only supported through the ansible galaxy cli. Once a valid ansible.cfg is setup, run the `ansible-galaxy role import` command to import one of your roles hosted on https://github.com

`ansible-galaxy role import <github_user> <github_repo>`

#### Role Versions

Role versions are derived from semantic version compliant git tags. During the import process, the backend looks for any git tag that is semver compatible (with the preceding v or V removed) and adds those as role versions.

## Updating Roles

Roles are "updated" by re-importing them.

`ansible-galaxy role import <github_user> <github_repo>`

## Deleting Roles

Roles can be deleted either via the ansible-galaxy CLI or with any http client (curl for example).

### ansible-galaxy CLI

`ansible-galaxy role delete <github_user> <github_repo>`

### http client

First, find the exact role id you'd like to delete.

`curl https://galaxy.ansible.com/api/v1/roles/?owner__username=<NAMESPACE_NAME>&name=<ROLE_NAME>`

Now issue a DELETE call to the role via it's full url.

`curl -X DELETE -H 'Authorization: token <TOKEN>' https://galaxy.ansible.com/api/v1/roles/<ROLE_ID>/`


## Changing Roles

Every role has a unique identifier which we call the "fully qualified name", FQN for short. If the role's name or namespace name are changed, installations of the previous FQN will fail.

In many cases the FQN matches the `github_user` and `github_repo`, but there are many exceptions. For example, many roles are hosted in github repositories named `ansible-role-<ROLENAME>`. At import time, the backend server will auto-trim the `ansible-role-` prefix to create the role's true name. There are also cases where an admin created a custom namespace in the old galaxy for a user and then through the UI a role was imported into that specific namespace, because the CLI wouldn't have been able to handle it. There are also cases where the github_user or github_repo were renamed on github which lead to an FQN that no longer matched those attributes.

Having a role FQN that does not closely resemble the github_user and github_repo the role comes from can lead to various problems:

* Naming collisions.
  * If a user changes their github login without changing the role namespace&github_user, the old login can be reclaimed by anyone and the integrity of galaxy's ownership for the roles is compromised.
  * If someone else besides the role auther currently has a matching github login, that person will be forced to use a different namespace in galaxy should they ever use the system.
* Confusion.
  * If a user's github login got created as a custom namespace by someone else before they ever log into galaxy, users aren't going to know which namespace is the true person.
  * A role user knows to install by the FQN as that is what is referenced on blog posts or other social media and what goes into requirements.yml. If the role namespace or name change, all of those internet references are no longer valid. The users will have to come to galaxy and try to find what the role has been renamed to via the search.
  * Curators and admins of galaxy spend a lot of time trying to sort out why github user "foo" doesn't own namespace "bar" or why "Foo" doesn't own "foo" or why "jimbob" can't import roles into "jimB0B".

### Changing the namespace name or the github_user

Should you decide that your roles would be better under a different namespace or github_user, here is the suggested path ... 

1. Delete the roles by ID as they currently exist on galaxy.
2. Create a new username on github.
3. Move the roles's github repositories to the new github username.
4. Login to galaxy with the new github username. (Namespaces will auto-create at login time)
5. Create a galaxy API token for the new username.
6. Re-import the roles from their new location. `ansible-galaxy role import <new_github_user> <reponame>`

We suggest picking a github username that is all lowercase, starts with a letter and does not contain hyphens. That ensures that no name conversion will be necessary for the corresponding collection namespace where ownership will be controlled.

### Changing the github_repository

1. Delete the role by it's current ID with an HTTP client..
2. Rename the roles's github repository to a new name.
3. Re-import the role from the new location. `ansible-galaxy role import <github_user> <new_repository_name>`

### Changing the role name

There are two ways to accomplish this and both involve re-importing the role.

A. `ansible-galaxy role import --role-name=<NEW_NAME> <github_user> <github_repo>`
B. Alter the `name` field in the role's `meta/main.yml` file and then import `ansible-galaxy role import <github_user> <github_repo>`

The second option is much more predictable and reliable.


## Uploading Collections

Collections can be uploaded either by the ansible galaxy CLI or in the GalaxyNG web interface.

### Galaxy CLI

`ansible-galaxy collection publish --help`

### Web Interface

1. In the left-nav click on "Collections"
2. Click on "Namespace"
3. In the center page, click on the tab in the upper middle that says "My namespaces"
4. Click "view collections" on one of the namespaces listed.
5. If the collection has no previous versions, click on the blue "Upload Collection" button and follow the prompts.
6. If the collection has previous versions, click the vertical 3 dot hamburger menu on the upper right and choose "upload new version" and then follow the prompts.
