# galaxy_ng/insights
# nothing
## Usage

**NOTE**: This will not work with the galaxy_ng/ui profile. To run the UI follow the instructions here: https://github.com/ansible/ansible-hub-ui#develop-in-insights-mode.

Run galaxy ng with the configurations required to launch in insights mode for developing on console.redhat.com.

This profile also provides an insights proxy implementation running on localhost:8080 that spoofs the authentication for console.redhat.com to facilitate in testing and API development. This supports basic and token authentication.


### Use the proxy with basic auth

A list of supported users can be found in `USERS` in `proxy/flaskapp.py`. Any password can be sent with any user.

```bash
# curl the API via the insights proxy using basic auth.

curl -u jdoe:pass  http://localhost:8080/api/automation-hub/_ui/v1/me/ | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1179  100  1179    0     0   5614      0 --:--:-- --:--:-- --:--:--  5614
{
  "id": 3,
  "username": "jdoe",
  "first_name": "john",
  "last_name": "doe",
  "email": "jdoe@redhat.com",
  "groups": [
    {
      "id": 3,
      "name": "rh-identity-account:6089719"
    }
  ],
  "date_joined": "2022-08-19T21:22:22.157581Z",
  "is_superuser": false,
  "auth_provider": [
    "django"
  ],
  "model_permissions": {
    "add_namespace": false,
    "upload_to_namespace": false,
    "change_namespace": false,
    "delete_namespace": false,
    "move_collection": false,
    "delete_collection": false,
    "add_remote": false,
    "change_remote": false,
    "delete_remote": false,
    "view_distribution": false,
    "add_distribution": false,
    "change_distribution": false,
    "delete_distribution": false,
    "add_containernamespace": false,
    "change_containernamespace": false,
    "delete_containernamespace": false,
    "add_containerrepository": false,
    "change_containerrepository": false,
    "delete_containerrepository": false,
    "add_containerregistry": false,
    "change_containerregistry": false,
    "delete_containerregistry": false,
    "add_containerdistribution": false,
    "change_containerdistribution": false,
    "delete_containerdistribution": false,
    "view_task": false,
    "view_user": false,
    "change_group": false,
    "view_group": false,
    "delete_user": false,
    "change_user": false,
    "add_user": false,
    "add_group": false,
    "delete_group": false
  },
  "is_anonymous": false
}
```

### Use the proxy with auth headers

A list of supported tokens can be found in `REFRESH_TOKENS` in `proxy/flaskapp.py`.

```bash
# Get your access token
curl -d "refresh_token=1234567890" -X POST localhost:8080/auth/realms/redhat-external/protocol/openid-connect/token
{
  "access_token": "f4a0b6d4-86b0-4428-a166-3f38fed03571"
}

# Curl the API
curl -H 'Authorization: Bearer f4a0b6d4-86b0-4428-a166-3f38fed03571' http://localhost:8080/api/automation-hub/_ui/v1/me/ | jq
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1179  100  1179    0     0   3221      0 --:--:-- --:--:-- --:--:--  3212
{
  "id": 3,
  "username": "jdoe",
  "first_name": "john",
  "last_name": "doe",
  "email": "jdoe@redhat.com",
  "groups": [
    {
      "id": 3,
      "name": "rh-identity-account:6089719"
    }
  ],
  "date_joined": "2022-08-19T21:22:22.157581Z",
  "is_superuser": false,
  "auth_provider": [
    "django"
  ],
  "model_permissions": {
    "add_namespace": false,
    "upload_to_namespace": false,
    "change_namespace": false,
    "delete_namespace": false,
    "move_collection": false,
    "delete_collection": false,
    "add_remote": false,
    "change_remote": false,
    "delete_remote": false,
    "view_distribution": false,
    "add_distribution": false,
    "change_distribution": false,
    "delete_distribution": false,
    "add_containernamespace": false,
    "change_containernamespace": false,
    "delete_containernamespace": false,
    "add_containerrepository": false,
    "change_containerrepository": false,
    "delete_containerrepository": false,
    "add_containerregistry": false,
    "change_containerregistry": false,
    "delete_containerregistry": false,
    "add_containerdistribution": false,
    "change_containerdistribution": false,
    "delete_containerdistribution": false,
    "view_task": false,
    "view_user": false,
    "change_group": false,
    "view_group": false,
    "delete_user": false,
    "change_user": false,
    "add_user": false,
    "add_group": false,
    "delete_group": false
  },
  "is_anonymous": false
}
```

## Extra Variables

*List any extra variables that user's can configure in their .compose.env*

None.