---
tags:
  - on-premise
  - auth
---

# How to use LDAP for Authentication

Galaxy can use `django_auth_ldap` package to enable LDAP integration, more info about the plugin can
be found on the plugin docs at: https://django-auth-ldap.readthedocs.io/ 

## Requirements

A running and acessible `LDAP` or `AD` server.

!!! tip
    For testing purposes you can start an openldap testing server using
    `https://github.com/rroemhild/docker-test-openldap` this server runs on `10389` port.


Checking if your ldap server is up and running:

> You need ldap-utils installed on your local host

```bash
# List all users
ldapsearch -H ldap://localhost:10389 -x -b "ou=people,dc=planetexpress,dc=com" -D "cn=admin,dc=planetexpress,dc=com" -w GoodNewsEveryone "(objectClass=inetOrgPerson)"

# List all groups
ldapsearch -H ldap://localhost:10389 -x -b "ou=people,dc=planetexpress,dc=com" -D "cn=admin,dc=planetexpress,dc=com" -w GoodNewsEveryone "(objectClass=Group)"
```

## Enabling Galaxy LDAP integration


The following settings can be added to either `/etc/pulp/settings.py` or exported as environment
variables prefixed with `PULP_`.

!!! note
    when using AAP Platform installer the variables are set under `automationhub_ldap` and `ldap_extra_settings` on the installer inventory file.

Example using environment variables:

!!! tip
    To set those variables using `/etc/pulp/settings.py` remove `PULP_` prefix and instead of toml formatting
    declare as normal python objects such as bools, lists and dictionaries.


Authentication class and deployment mode by default is already set tho the following values, 
You don't need to change it, **just confirm this is the setting you have in place.**

```bash
PULP_GALAXY_AUTHENTICATION_CLASSES=['galaxy_ng.app.auth.session.SessionAuthentication','rest_framework.authentication.TokenAuthentication','rest_framework.authentication.BasicAuthentication']
PULP_GALAXY_DEPLOYMENT_MODE=standalone
```

Pulp container requires this to be set in order to provide docker registry compatible token authentication.
https://docs.pulpproject.org/pulp_container/authentication.html

```bash
PULP_TOKEN_AUTH_DISABLED=true
```

### Required setting

For `django_auth_ldap` to be included as the first authentication backend, there is a preset called
`ldap`

```bash
PULP_AUTHENTICATION_BACKEND_PRESET=ldap
```

#### customizing the order of authentication backends 

Set `PULP_AUTHENTICATION_BACKEND_PRESET` to `custom` if you really want to override `PULP_AUTHENTICATION_BACKENDS` variable, this might be useful if you need to change the order of evaluated backends.

<details>
<summary>Example</summary>


```python
AUTHENTICATION_BACKEND_PRESET='custom'
# arrange the order
AUTHENTICATION_BACKENDS=[
  "django.contrib.auth.backends.ModelBackend",
  "pulpcore.backends.ObjectRolePermissionBackend",
  "galaxy_ng.app.auth.ldap.GalaxyLDAPBackend",
]
```

</details>


### Required Specific django_auth_ldap settings

!!! tip
    depending on the LDAP server some of the following settings might need change.

The following keys are **required** in order to have LDAP enabled:

```bash
PULP_AUTH_LDAP_SERVER_URI="ldap://ldap:10389"
PULP_AUTH_LDAP_BIND_DN="cn=admin,dc=planetexpress,dc=com"
PULP_AUTH_LDAP_BIND_PASSWORD="GoodNewsEveryone"
PULP_AUTH_LDAP_USER_SEARCH_BASE_DN="ou=people,dc=planetexpress,dc=com"
PULP_AUTH_LDAP_USER_SEARCH_SCOPE="SUBTREE"
PULP_AUTH_LDAP_USER_SEARCH_FILTER="(uid=%(user)s)"
PULP_AUTH_LDAP_GROUP_SEARCH_BASE_DN="ou=people,dc=planetexpress,dc=com"
PULP_AUTH_LDAP_GROUP_SEARCH_SCOPE="SUBTREE"
PULP_AUTH_LDAP_GROUP_SEARCH_FILTER="(objectClass=Group)"
PULP_AUTH_LDAP_GROUP_TYPE_CLASS="django_auth_ldap.config:GroupOfNamesType"
```

### Customizing Group Type

In some cases you might want to use a different group type class, for example if you want to use
`MemberDNGroupType` you can set it but also have to set AUTH_LDAP_GROUP_TYPE_PARAMS as follows:

```bash
PULP_AUTH_LDAP_GROUP_TYPE_CLASS="django_auth_ldap.config:MemberDNGroupType"
PULP_AUTH_LDAP_GROUP_TYPE_PARAMS={name_attr="cn", member_attr="member"}
```

> NOTE: the above example exports data as environment variables so it uses the TOML format
> to describe a dictionary object, if you are adding those settings to `/etc/pulp/settings.py`
> you need to declare it as a regular python dictionary object.
> another option is to export as 
> `PULP_AUTH_LDAP_GROUP_TYPE_PARAMS='@json {"name_attr": "cn", "member_attr": "member"}'`

### Optional variables:

```bash
PULP_AUTH_LDAP_USER_ATTR_MAP={first_name="givenName", last_name="sn", email="mail"}
# NOTE: the above is formatted as a toml hashmap

PULP_AUTH_LDAP_MIRROR_GROUPS=true
# The above is what enabled group mirroring
# the same variable also accepts a list of groups to mirror
PULP_AUTH_LDAP_MIRROR_GROUPS=['admin_staff', 'ship_crew']
```

You can limit which groups are mirrored if you don't want all the groups to be added do Hub.

```bash
PULP_AUTH_LDAP_MIRROR_GROUPS_EXCEPT=['foobar']
# this syncs all groups except the `foobar`
```

Require a specific group for all users

```bash
PULP_AUTH_LDAP_REQUIRE_GROUP='hub_users'
# Only users belonging to this group will be allowed to login
```

### Mirroring only existing groups on Hub

```bash
PULP_GALAXY_LDAP_MIRROR_ONLY_EXISTING_GROUPS=true
```

When set to `true` only groups that already exist on Hub will be mirrored,
this means that users will login but not all the user groups from LDAP
will be mirrored, the authentication backend will map to the user only
the groups that matches the same name of groups existing in Hub.

!!! note
  When this option is set the variable `AUTH_LDAP_MIRROR_GROUPS` will
  be automatically set to `true` and `AUTH_LDAP_MIRROR_GROUPS_EXCEPT` will default
  to `false` regardless of the value you set for those 2 variables.

### Mapping groups from LDAP to user attributes on Django:

Ex: Users belonging to `admin_staff` on LDAP is `superuser` on Django.

```bash
PULP_AUTH_LDAP_USER_FLAGS_BY_GROUP__is_superuser="cn=admin_staff,ou=people,dc=planetexpress,dc=com"
```

And the same logic can be applied to any other attribute:

```bash
PULP_AUTH_LDAP_USER_FLAGS_BY_GROUP__is_staff="cn=ship_crew,ou=people,dc=planetexpress,dc=com"
```


Or optionally put on `/etc/pulp/setting.py`

```python
AUTH_LDAP_USER_FLAGS_BY_GROUP = {
    "is_active": "cn=active,ou=groups,dc=example,dc=com",
    "is_staff": (
        LDAPGroupQuery("cn=staff,ou=groups,dc=example,dc=com")
        | LDAPGroupQuery("cn=admin,ou=groups,dc=example,dc=com")
    ),
    "is_superuser": "cn=superuser,ou=groups,dc=example,dc=com",
}
```

### TLS verification

```bash
# Make ldap to call start_tls on connections
PULP_AUTH_LDAP_START_TLS=true

# If using self signed certificates set this
PULP_GALAXY_LDAP_SELF_SIGNED_CERT=true
```

### Logging:

```bash
# Enable LDAP logging handler
PULP_GALAXY_LDAP_LOGGING=true
```

### Cache

```bash
# Change the caching lifetime in seconds (for groups and users search)
PULP_AUTH_LDAP_CACHE_TIMEOUT=3600
```

### LDAP REferrals

MS Active Directory but search operation may result in the exception `ldap.OPERATIONS_ERROR` with the diagnostic message text “In order to perform this operation a successful bind must be completed on the connection.” Alternatively, a Samba 4 AD returns the diagnostic message “Operation unavailable without authentication”. 

To fix that problem the LDAP REFERALS lookup can be disabled:

```bash
PULP_GALAXY_LDAP_DISABLE_REFERRALS=true
```

The above will set the proper option to `AUTH_LDAP_CONNECTION_OPTIONS` in the settings.

---

More settings can be found on https://django-auth-ldap.readthedocs.io/en/latest/reference.html#settings
