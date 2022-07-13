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


Example using environment variables:

!!! tip
    To set those variables using `/etc/pulp/settings.py` remove `PULP_` prefix and instead of toml formatting
    declare as normal python objects such as bools, lists and dictionaries.


Authentication class and deployment mode by default is already set tho the following values, 
You don't need to change it, **just confirm this is the setting you have in place.**

```bash
PULP_GALAXY_AUTHENTICATION_CLASSES=['rest_framework.authentication.SessionAuthentication','rest_framework.authentication.TokenAuthentication','rest_framework.authentication.BasicAuthentication']
PULP_GALAXY_DEPLOYMENT_MODE=standalone
```

Pulp container requires this to be set in order to provide docker registry compatible token authentication.
https://docs.pulpproject.org/pulp_container/authentication.html

```bash
PULP_TOKEN_AUTH_DISABLED=true
```

`django_auth_ldap` must be included as the first authentication backend, there is a preset called
`ldap` (you can set it to `custom` if you really want to override `PULP_AUTHENTICATION_BACKENDS` variable)

```bash
PULP_AUTHENTICATION_BACKEND_PRESET=ldap
```

Specific django_auth_ldap settings

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
PULP_AUTH_LDAP_GROUP_SEARCH_FILTER = "(objectClass=Group)"
PULP_AUTH_LDAP_GROUP_TYPE_CLASS="django_auth_ldap.config:GroupOfNamesType"
```

Optional variables:

```bash
PULP_AUTH_LDAP_USER_ATTR_MAP={first_name="givenName", last_name="sn", email="mail"}
# NOTE: the above is formatted as a toml hashmap

PULP_AUTH_LDAP_MIRROR_GROUPS=true
# The above is what enabled group mirroring
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

Mapping groups from LDAP to user attributes on Django:

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

TLS verification

```bash
# Make ldap to call start_tls on connections
PULP_AUTH_LDAP_START_TLS=true

# If using self signed certificates set this
PULP_GALAXY_LDAP_SELF_SIGNED_CERT=true
```

Logging:

```bash
# Enable LDAP logging handler
PULP_GALAXY_LDAP_LOGGING=true
```

Cache

```bash
# Change the caching lifetime in seconds (for groups and users search)
PULP_AUTH_LDAP_CACHE_TIMEOUT=3600
```


More settings can be found on https://django-auth-ldap.readthedocs.io/en/latest/reference.html#settings
