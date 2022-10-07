# galaxy_ng/keycloak

## Usage

Launch galaxy_ng with configuration for running Keycloak.

This will automatically configure keycloak and pulp with the correct `SOCIAL_AUTH_KEYCLOAK_PUBLIC_KEY` setting
by running the `keycloak-playbook.yaml` playbook in the pulp container during boot.

To access keycloak, open localhost:8080 in your browser. From there you can login to the administrator panel with
the admin/admin credentials. Galaxy is configured under the "Aap" realm. You can see a list of available users
here and promote any of them to a super user role by appling the `hubadmin` role to any of the listed users.
To assign a role, select the user from the list of users, navegate to the "Role Mapping" tab, click "Assign Role",
select "Filter by clients" from the filter dropdown and assign the `hubadmin` role.

The login for each user is the same as their username. Some users you can choose from are (username/password):

- amy/amy
- bender/bender
- fry/fry
- hermes/hermes
- leela/leela
- professor/professor
- zoidberg/zoidberg
