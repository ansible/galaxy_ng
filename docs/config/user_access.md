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
