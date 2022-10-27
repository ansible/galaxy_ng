# Community User Guide

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

Standalone roles are not yet presented in the UI, so search is only available via the api or galaxy cli.

The v1 rest api has filter parameter support similar to the current code on https://galaxy.ansible.com.

```bash
# Find all roles created by a specific github user.
curl 'https://beta-galaxy.ansible.com/api/v1/roles/?github_user=geerlingguy'

# Find all roles containing a keyword in the namespace, name or description.
curl 'https://beta-galaxy.ansible.com/api/v1/roles/?keyword=docker'
```

The ansible-galaxy CLI also supports role search

```bash
ansible-galaxy role search --help
```


## Finding Collections
Collections do have search support in the UI.

1. In the left-nav click "Collections".
2. Choose the appropriate repository in the dropdown.
3. Choose keywords or tag.
4. Type the term or select a tag to filter the list of results.

!!! info

    What repository?

    We're currently synchronizing all collections from https://galaxy.ansible.com into the "community" repository,
    but will soon attempt to change that to the "published" repository.

Future support for collection search in the ansible-galaxy CLI is [TBD](https://issues.redhat.com/browse/AAH-1968).


## Installing Roles

Role installs should work as they did before with https://galaxy.ansible.com


## Installing Collections

Collection installs should work as they did before with https://galaxy.ansible.com


## Importing Roles

Role imports are only supported through the ansible galaxy cli. Once a valid ansible.cfg is setup, run the `ansible-galaxy role import` command to import one of your roles hosted on https://github.com

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
