# Configuration

Galaxy NG is a Pulp Plugin and the configuration system is based on Pulp's configuration
you can find more information about pulp configuration on [Pulp Docs](https://docs.pulpproject.org/pulpcore/configuration/index.html)


!!! tldr
    [Click here to jump to the list of configuration options](#configuration-options)


!!! tip
    If you are looking for how to se configuration options on the pulp-installer take a look on [installation page](/installation)

## Configuring your galaxy server

There are 2 sources of custom configurations for a Galaxy server the custom **settings file** and **environment variables**.


### Settings File

By default the settings file is placed under `/etc/pulp/settings.py` and is a Python file containing Python
constants (`UPPER_SNAKE_CASE` variables) with configuration values.

Example:

```py title="/etc/pulp/settings.py"
GALAXY_REQUIRE_CONTENT_APPROVAL = True
GALAXY_COLLECTION_SIGNING_SERVICE = "ansible-default"
GALAXY_ENABLE_API_ACCESS_LOG = True
```

The variables prefixed with `GALAXY_` are specific to the Galaxy application while there are also
unprefixed variables that are either pulp settings or django framework settings.

Example:

```py title="/etc/pulp/settings.py"
DEBUG = False
AUTH_USER_MODEL = 'galaxy.User'
X_PULP_CONTENT_HOST = "localhost"
```

!!! warning
    In most of the cases the only variables you may want to customize are those prefixed with `GALAXY_`
    and a small subset of pulp control variables taht you can check on the configuration list provided
    on the [bottom of this page.](#configuration-options)


### Environment variables

As Galaxy NG is a pulp plugin it assumes the envvar prefix as `PULP_` so any variable can be 
customized by export a `PULP_<followed_with_the_variable>`, example:

```bash title="environment"
export PULP_GALAXY_REQUIRE_CONTENT_APPROVAL=true
```

!!! tip
    Pulp uses [dynaconf](dynaconf.com) to manage its settings, so environment variables have its
    data types inferred, for example: `PULP_NUMBER=4.2` will be available under `django.conf.settings.NUMBER` 
    as a value of type `float`, if you need to force a string enclose on quotes. `PULP_TEXT='4.2'`


**Environment Variables** have the higher precedence and will always override the values set on the
settings file or the default settings on galaxy or pulp applications.


### Merging configurations

Dynaconf provides extensive docs on [how to merge with existing values](https://www.dynaconf.com/merging/)
and this is useful when there is already a compound data structure on the settings such as a list or a dictionary
and you want to contribute to it instead of replacing.

#### Examples:

**Merging to dictionaries:**

On `galaxy_ng.app.settings` there is

```py title="Galaxy internal default config"
GALAXY_FEATURE_FLAGS = {
    'execution_environments': True,
}
```

If you need to add an additional feature flag without replacing the existing value:

```py title="/etc/pulp/settings.py"
GALAXY_FEATURE_FLAGS = {
    "my_new_feature_flag": True,
    "dynaconf_merge": True  #(1)
}
```

1. This marks this settings to be merged with existing

And there is a Django style shortcut for the same as above:

```py title="/etc/pulp/settings.py"
GALAXY_FEATURE_FLAGS__my_new_feature_flag = True
```

Notice the `__` double underscores to denote the nesting structure.


!!! tip
    the merge can also be done on environment variables, just export using `__`


**Merging to lists**

Assuming that on `galaxy_ng.app.settings` there is the default

```py title="Galaxy internal default config"
GALAXY_AUTHENTICATION_CLASSES = [
    "rest_framework.authentication.SessionAuthentication",
    "rest_framework.authentication.TokenAuthentication",
    "rest_framework.authentication.BasicAuthentication",
]
```

And you need to add a new custom value you can do

```py title="/etc/pulp/settings.py"
GALAXY_AUTHENTICATION_CLASSES = [
    "my.new.AuthClass",
    "dynaconf_merge" #(1)  
]
```

1. This marks this settings to be merged with existing

And also there is a shortcut useful for environment variables using `@merge` mark.

```bash title="environment"
export GALAXY_AUTHENTICATION_CLASSES="@merge my.new.AuthClass"
```

On all the cases the `my.new.AuthClass` will be appended to the end of the existing list.


### Settings sources

Here is a [diagram explaining](https://www.xmind.net/m/VPSF59/#) the loading order of the settings on a Pulp System

<iframe src='https://www.xmind.net/embed/VPSF59/' width='750' height='438' frameborder='0' scrolling='no' allowfullscreen="true"></iframe>


## Configuration Options

### Galaxy

| Variable name                                    | Description                          |
| ----------------------------------------------   | ------------------------------------ |
| `GALAXY_API_PATH_PREFIX`                         | The base url to access API endpoints, Default:`"/api/galaxy"` |
| `GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH`      | Distribution where collections go after approved, Default: `"published"` |
| `GALAXY_API_STAGING_DISTRIBUTION_BASE_PATH`      | Distribution where collections go when waiting for approval, Default: `"staging"` |
| `GALAXY_API_REJECTED_DISTRIBUTION_BASE_PATH`     | Distribution where collections go after rejection, Default: `"rejected"` |
| `GALAXY_REQUIRE_CONTENT_APPROVAL`                | Sets if system requires uploaded collections to be manually approved, Default: `True` (if set to false all uploaded collections are automatically approved)  |
| `GALAXY_FEATURE_FLAGS`                           | A dictionary that toggles specific flags [see feature flags page](/featureflags) |
| `GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_ACCESS`      | Enabled anonymous browsing, Default: `False` |
| `GALAXY_ENABLE_UNAUTHENTICATED_COLLECTION_DOWNLOAD`      | Enabled anonymous download, Default: `False` |
| `GALAXY_ENABLE_API_ACCESS_LOG`      | Enable gathering of logs, Default: `False` |
| `GALAXY_ENABLE_API_ACCESS_LOG`      | Enable gathering of logs, Default: `False` |
| `CONNECTED_ANSIBLE_CONTROLLERS`      | List of controllers connected , Default: `[]` |
| `CONTENT_PATH_PREFIX`      | URL prefix for content serving , Default: `"/api/automation-hub/v3/artifacts/collections/"` |
| `GALAXY_AUTHENTICATION_CLASSES`      | List of auth classes for DRF , Default: `[Session, Token, Basic]` |
| `GALAXY_PERMISSION_CLASSES`      | List of classes for permission backend , Default: `[]` |
| `GALAXY_AUTO_SIGN_COLLECTIONS`      | Set if system sign collections upon approval , Default: `False` |
| `GALAXY_COLLECTION_SIGNING_SERVICE`  | The signing service to use for signing , Default: `ansible-default` |


For SSO Keycloak configuration see [keycloak](keycloak)

### Pulp, Django and other plugins

| Variable name                                    | Description                          |
| ----------------------------------------------   | ------------------------------------ |
| `CONTENT_BIND`      | Pulp app content bind ex: `unix:/path/to/socker.sock`, Default: `None` |
| `DEFAULT_FILE_STORAGE`      | Sets the storage backend , ex: `'storages.backends.s3boto3.S3Boto3Storage'` Default: `None` |
| `ANSIBLE_API_HOSTNAME`      | Hostname for the Ansible API, Default: `same as PULP_CONTENT_ORIGIN` |

For more configuration options for pulp check on [https://docs.pulpproject.org/pulpcore/configuration/index.html](https://docs.pulpproject.org/pulpcore/configuration/index.html)