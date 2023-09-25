# Community Galaxy Administration


## Creating a new v3 namespace

V3 Namespaces can be created in one of two methods: API or WebUI.

### WebUI

1) Login as a superuser
2) Expand "Collections" in the left nav
3) Click on "Namespaces" in the left nav
4) Click the "Create" button in the middle of the top header.
5) Fill in an appropriate name.
6) Click "Create" to save.
7) In the summary page for the new namespace, click on the 3 dot hamburger icon on the top right.
8) Choose "Edit Namespace" from the menu.
9) Fill in the various details such as the company name, logo url, and description.
10) Click "Save"

### API

```
$ curl -X POST \
    -H 'Authorization: token <TOKEN>' \
    -H 'Content-Type: appliction/json' \
    -d '{"name": "foobar", "groups": []}' \
    https://galaxy-dev.ansible.com/api/_ui/v1/namespaces/
```

TBD: Setting namespace details via the API.

## Setting namespace owners

Social auth in galaxy_ng has been heavily customized per https://github.com/ansible/galaxy_ng/pull/1881

A "legacy" namespace is the api/v1 style namespace that allows any valid github username as the name.

A "v3" namespace is the api/v3 and pulp related namespace which is restricted to allowable python package names because of v3 being solely focused on ansible collections.

The legacy namespaces should have a foreign key relationship with a v3 namespace (which we'll call the "provider" namespace). The provider namespace is where owner management should occur.

A user on galaxy should be able to import roles into their legacy namespace, and also upload collections to their provider namespace (or any v3 namespace they've been added to). As the user logs into galaxy, the backend should validate and create their legacy namespace and the provider/v3 namespace automatically.



#### Validating and fixing a user via the django shell

```
pulpcore-manager shell
from galaxy_ng.app.models import User
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.models import Namespace
from galaxy_ng.app.utils import rbac
from pulpcore.plugin.util import get_groups_with_perms_attached_roles
from pulpcore.plugin.util import get_users_with_perms_attached_roles

# find the user ...
sean = User.objects.filter(username='sean-m-sullivan').first()

# find the user's legacy namespace ...
legacy_namespace = LegacyNamespace.objects.filter(name='sean-m-sullivan').first()
assert legacy_namespace is not None

# check the "provider" namespace of the legacynamespace ...
provider_namespace = legacy_namespace.namespace
assert provider_namespace is not None

# get a list of owners for the provider namespace ...
owners = rbac.get_v3_namespace_owners(provider_namespace)
assert sean in owners
```

To fix sean's RBAC on the sean-m-sullivan/sean_m_sullivan namespaces ...
```
provider_namespace = Namespace.objects.filter(name='sean_m_sullivan').first()
rbac.add_user_to_v3_namespace(sean, provider_namespace)
owners = rbac.get_v3_namespace_owners(provider_namespace)
assert sean in owners

legacy_namespace.namespace = provider_namespace
legacy_namespace.save()
```

To fix sean's RBAC on the Wilk42/wilk42 namespaces ...
```
legacy_namespace = LegacyNamespace.objects.filter(name='Wilk42').first()
# this legacy namespace already had the provider namespace of wilk42
rbac.add_user_to_v3_namespace(sean, legacy_namespace.namespace)
owners = rbac.get_v3_namespace_owners(legacy_namespace.namespace)
assert sean in owners
```

#### Validating and fixing a user via the API

Find the legacy namespace ...
```
curl https://galaxy-dev.ansible.com/api/v1/namespaces/?name=Wilk42 | jq .
```

Check the provider namespace ...
```
$ curl -s https://galaxy-dev.ansible.com/api/v1/namespaces/?name=Wilk42 | jq .results[0].summary_fields.provider_namespaces
[
  {
    "id": 19193,
    "name": "wilk42",
    "pulp_href": "/api/pulp/api/v3/pulp_ansible/namespaces/19193/"
  }
]
```

Binding a provider namespace to the legacy namespace ...
```
$ curl -X POST \
    -H 'Authorization: token <TOKEN>' \
    -H 'Content-Type: appliction/json' \
    -d '{"id": 19192}' \
    https://galaxy-dev.ansible.com/api/v1/namespaces/7532/providers/
```

Check the owners ...
```
$ curl -s https://galaxy-dev.ansible.com/api/v1/namespaces/?name=Wilk42 | jq .results[0].summary_fields.
owners
[
  {
    "id": 7184,
    "username": "Wilk42"
  },
  {
    "id": 17656,
    "username": "sean-m-sullivan"
  }
]
```

Setting the list of owners for a provider namespace ...
```
$ curl -X POST \
    -H 'Authorization: token <TOKEN>' \
    -H 'Content-Type: appliction/json' \
    -d '{"owners": [{"id": 7184}, {"id": 17656}]}' \
    https://galaxy-dev.ansible.com/api/v1/namespaces/7532/owners/
```

## Deleting legacy roles

Legacy role RBAC should allow superusers and legacy namespace owners to delete their owned roles ...

```
$ curl -X DELETE \
    -H 'Authorization: token <TOKEN>' \
    https://galaxy-dev.ansible.com/api/v1/roles/<roleid>/
```

The API does not currently support deleting a specific legacy role version.


## Deleting collections
