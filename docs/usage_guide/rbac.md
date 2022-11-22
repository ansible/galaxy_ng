# RBAC and User Management

## Roles and Permissions

Galaxy NG uses a role based permissioning system based off of Django's permission model. Permissions are grouped into roles and roles are assigned to users via groups. For example if a user wishes to grant an account the permission to add users and groups, they could create a role that has the following permissions and assign the role to the user's group:

- Add user
- View users
- Add group
- View groups

Ultimately the app only ever checks permissions, however permissions can't be assigned directly, they must be assigned via roles.

To create new roles navigate to "User Access > Roles". This page administrators to create and edit existing roles. Galaxy NG also ships with a predefined set of roles by default, which should cover most of the use cases.

User's can also be granted super user status. This bypasses the permissioning system and grants the user access to every action. Super user status can only be granted by other super users, and is available by going to "User Access > Users" and selecting edit on a user.

## Global Roles

Global roles are roles that give a user access to all objects of a specific type. For example assigning a role with the "edit namespaces" permission globally will grant any user with the role access to edit any namespace in the system.

Global roles can be assigned to groups via the "User Access > Groups" page. From here select a group to edit and navigate to the "Access" tab. All the roles assigned to the group can be viewed, added and removed here.

## Object Roles

Object roles are assigned to a specific instance of an object, and only grant the user to perform actions on those individual objects. For example a user who is assigned a role with the "Edit namespace" permission on the namespace `foo` will only be able to edit the namespace `foo`, not any other namespace.

!!! note
    If the user has object and global permissions, the global permissions take precedence, and they will be able to edit any instance of the given object.

Currently there are two places where object roles are used:

- [Collection namespaces](/galaxy_ng/usage_guide/collections#permissions)
- [Execution Environment namespaces](/galaxy_ng/usage_guide/execution_environments#permissions)
