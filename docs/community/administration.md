# Community Galaxy Administration

## Setting namespace owners

Social auth in galaxy_ng has been heavily customized per https://github.com/ansible/galaxy_ng/pull/1881

A "legacy" namespace is the api/v1 style namespace that allows any valid github username as the name.

A "v3" namespace is the api/v3 and pulp related namespace which is restricted to allowable python package names because of v3 being solely focused on ansible collections.

The legacy namespaces should have a foreign key relationship with a v3 namespace (which we'll call the "provider" namespace). The provider namespace is where owner management should occur.

A user on galaxy should be able to import roles into their legacy namespace, and also upload collections to their provider namespace (or any v3 namespace they've been added to). As the user logs into galaxy, the backend should validate and create their legacy namespace and the provider/v3 namespace automatically.

To validate a user via django shell, do the following:

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
```

To fix sean's RBAC on the sean-m-sullivan/sean_m_ullivan namespaces ...
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
