# User Authentication and Access


## Configuring Minimum Password Length

!!! info
    This setting is valid for internal Django users only, for keycloak users
    the rules must be configured on the SSo service.

When creating new users on internal database (Django Users) a validation is 
performed and one can configure the minimum password length.

The default value is 9 and can be customized using:

```python title="/etc/pulp/settings.py"
GALAXY_MINIMUM_PASSWORD_LENGTH=15
```

```bash title="envronment variables"
export PULP_GALAXY_MINIMUM_PASSWORD_LENGTH=15
```

## Auto logout after set period of time

Auto logout is configurable in Django by the `SESSION_COOKIE_AGE` variable

The default value is `1209600` (2 weeks, in seconds)

This default value can be changed, for exemple, to make session expire after 1 hour.

```python title="/etc/pulp/settings.py"
SESSION_COOKIE_AGE=3600
```

```bash title="envronment variables"
export PULP_SESSION_COOKIE_AGE=3600
```
