# RBAC in Galaxy NG

## Basics

### Permissions

Every object in a GalaxyNG has at least four permissions created for it by default:
- Add: grants the ability to add objects of that class
- Delete: grants the ability to delete objects of that class
- View: grants the ability to view objects of that class
- Update: grants the ability to update objects of that class

Additional custom permissions can also be created for objects. For example, the `namespace` object has the "Upload to namespace" custom permission that we have defined to allow users to upload collections to a specific namespace.

### Roles

Roles are groups of permissions that can be assigned to groups. There are a set of predefined roles that ship with GalaxyNG, however users can also define their own roles with any set of permissions that they want.

### Role Assignment

Roles can be assigned at two levels: model (global) and object.

This is different from other AAP components which allow organization-level and object-level permissions. Right now, organization level permissions are not possible because a related `organization` field does not exist on galaxy-specific resources like collections and namespaces. This might be added in the future to support organization-level roles.

Model roles are global, and grant the permission to all objects of the given class in the system. For example, granting model level namespace_owner role will allow a user to update all namespaces in the system.

Object level roles are for specific objects. They allow for a user in the system to be granted permissions for a specific object. For example, granting a user the namespace_owner role on namespace `foo` will allow a user to update namespace `foo`, but no other namespaces.

Roles can be assigned in one of two ways: on a per user level or on a per group level. At the moment, only group roles are supported. To grant permissions, an admin has to create a group with the desired set of roles and then add users who need those permissions to the group. For example an admin might create a "Content Managers" group that has global roles for creating and updating new collections, namespaces and EEs. This would allow the admin to grant new users all the permissions needed to manage content by adding them to the "Content Managers" group.

### Unused Permissions

In the pulp `Role` model, the standard permission model from `django.contrib.auth` app is used. This creates permissions for all models, even if they are unused.

Content types such as collections and execution environments don't require any special permissions to view, so the view permissions for collections and EEs aren't enforced.

### DAB RBAC

A unified RBAC system has been introduced, the DAB RBAC system.

#### Synchronization to pulp Role models

This is synchronized by Django signals with the pulp `Role` model to support existing APIs. The DAB RBAC system has its own permission model, which only includes permissions for models registered with DAB RBAC, so this model should not have unused permission entries.

#### Synchronization to Resource Server

Changes to role assignments may be synchronized with a connected "resource server" as a new feature.
This makes requests to the "resource server" using a client from the [DAB resource_registry](https://github.com/ansible/django-ansible-base/tree/devel/ansible_base/resource_registry) app. These requests are made from DAB code so the logic will not be found within galaxy_ng.

To support synchronization, DAB RBAC uses a custom `DABContentType` model which resembles the Django contrib `ContentType` model.
This adds an additional `service` field on the model, but for all resources owned by galaxy_ng will just have "galaxy" for that field.
Models that are managed by the resource server, right now organization and team, will have "shared" for the service field.
The point of the custom DAB RBAC content type model is to save permissions for models in other systems, but that is not done here,
only the shared and local models are tracked by RBAC in galaxy_ng.

### Super users

Users with django super user permissions automatically have all permissions in the system and can do anything that the app allows.

## Technical Details

To make all of this work, we use two external libraries that add some addition functionality to the existing Django RBAC system.

### Pulp RBAC

Pulp RBAC allows us to create roles that group together sets of django permissions and assign them to users and groups globally or for specific objects.

### DRF Access policy

DRF access policy (https://rsinger86.github.io/drf-access-policy/) allows us to create DRF permission classes that read a JSON or python object and return whether or not the user has permissions to perform some action. A DRF access policy statement looks something like this:

```
[
        {
            "action": ["list", "retrieve"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "destroy",
            "principal": "*",
            "effect": "deny",
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:galaxy.add_namespace"
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:galaxy.change_namespace"
        },
    ]
```

This access policy allows for authenticated users to view content, users with the `galaxy.add_namespace` permissions to create new namespaces, users with the `change_namespace` permissions to update namespaces and denies everyone from deleting namespaces.

Our access policy definitions can be found in `galaxy_ng/galaxy_ng/app/access_control/statements`.

Note that we never reference roles directly in any of the access policies. Instead, access is granted based on what permissions a user has. Those permissions are checked by looking up the user's roles and verifying that they have a role with the necessary set of permissions to perform some action.

#### Loading DRF Access policies

Access policies are loaded in `galaxy_ng/galaxy_ng/app/access_control/access_policy.py`. At the moment there are two sets of access policies, one for insights mode, which disables features that aren't allowed in insights mode and one for standalone mode, which enables features such as user management and collection syncing. When the app is loaded, the access policy base class checks if the app is running in insights mode or standalone mode and loads the corresponding access policy.

### Pulp Access Policies

Access policies for pulp api endpoints can be defined in our access policies by setting up an access policy that has the same url pattern as a pulp viewset. This access policy will apply to the group roles API.

```
'groups/roles': [
    {
        "action": ["list", "retrieve"],
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_model_perms:galaxy.view_group"
    },
    {
        "action": "create",
        "principal": "authenticated",
        "effect": "allow",
        "condition": "has_model_perms:galaxy.change_group"
    },
    {
        "action": "*",
        "principal": "admin",
        "effect": "allow"
    }
],
```

Pulp viewset url patterns are loosely based on their api path, but this isn't always the case. The best way to figure out which viewset name applies to an API endpoint is to throw a print statement here https://github.com/ansible/galaxy_ng/blob/63803c3c8f40450b7e9e5abcc63121487f80ab33/galaxy_ng/app/access_control/access_policy.py#L81 and see what the value for `viewname` is.