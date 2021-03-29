from django.db import migrations
from django.contrib.auth.management import create_permissions


viewsets = {
    # Note. This is the default Pulp Continer access policy with some modifications.
    # Our changes have been marked with comments.
    "distributions/container/container": {
        "statements": [
            {
                "action": ["list"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["catalog"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_perms:container.add_containerdistribution",
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_namespace_or_obj_perms:container.view_containerdistribution",
                ],
            },
            {
                "action": ["pull"],
                # Require authentication for container pull.
                # "principal": "*",
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "not is_private",
                ],
            },
            {
                "action": ["pull"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_namespace_or_obj_perms:container.pull_containerdistribution",
                ],
            },
            {
                "action": ["update", "partial_update"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:container.change_containerdistribution",
                    "has_namespace_or_obj_perms:container.view_containerdistribution",
                ],
            },
            {
                "action": ["push"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_namespace_or_obj_perms:container.push_containerdistribution",
                    "obj_exists",
                ],
            },
            {
                "action": ["push"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_namespace_or_obj_perms:container.add_containerdistribution",
                    "has_namespace_or_obj_perms:container.push_containerdistribution",
                ],
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_namespace_or_obj_perms:container.delete_containerdistribution",
                    "has_namespace_or_obj_perms:container.view_containerdistribution",
                ],
            },
        ],
        "permissions_assignment": [
            {
                "function": "create_distribution_group",
                "parameters": {
                    "group_type": "owners",
                    "add_user_to_group": True,
                },
                "permissions": [
                    "container.view_containerdistribution",
                    "container.pull_containerdistribution",
                    "container.push_containerdistribution",
                    "container.delete_containerdistribution",
                    "container.change_containerdistribution",
                ],
            },
            {
                "function": "add_push_repository_perms_to_distribution_group",
                "parameters": {
                    "group_type": "owners",
                },
                "permissions": [
                    "container.view_containerpushrepository",
                    "container.modify_content_containerpushrepository",
                ],
            },
            {
                "function": "create_distribution_group",
                "parameters": {
                    "group_type": "collaborators",
                    "add_user_to_group": False,
                },
                "permissions": [
                    "container.view_containerdistribution",
                    "container.pull_containerdistribution",
                    "container.push_containerdistribution",
                ],
            },
            {
                "function": "add_push_repository_perms_to_distribution_group",
                "parameters": {
                    "group_type": "collaborators",
                },
                "permissions": [
                    "container.view_containerpushrepository",
                    "container.modify_content_containerpushrepository",
                ],
            },
            {
                "function": "create_distribution_group",
                "parameters": {
                    "group_type": "consumers",
                    "add_user_to_group": False,
                },
                "permissions": [
                    "container.view_containerdistribution",
                    "container.pull_containerdistribution",
                ],
            },
            {
                "function": "add_push_repository_perms_to_distribution_group",
                "parameters": {
                    "group_type": "consumers",
                },
                "permissions": [
                    "container.view_containerpushrepository",
                ],
            },
        ],
    },

    "pulp_container/namespaces": {
        "statements": [
            {
                "action": ["list"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["create"],
                "principal": "authenticated",
                "effect": "allow",
                # Requiring permissions for namespaces creation means that
                # add_containernamespace is required for creating new repos,
                # along with add_containerdistribution which is confusing to
                # the end user.
                # "condition": "has_model_perms:container.add_containernamespace",
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:container.view_containernamespace",
            },
            {
                "action": ["destroy"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_model_or_obj_perms:container.delete_containernamespace",
                    "has_model_or_obj_perms:container.view_containernamespace",
                ],
            },
            {
                "action": ["create_distribution"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:container.namespace_add_containerdistribution",
            },
            {
                "action": ["view_distribution"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:container.namespace_view_containerdistribution",  # noqa: E501
            },
        ],
        "permissions_assignment": [
            {
                "function": "create_namespace_group",
                "parameters": {
                    "group_type": "owners",
                    "add_user_to_group": True,
                },
                "permissions": [
                    "container.view_containernamespace",
                    "container.delete_containernamespace",
                    "container.namespace_add_containerdistribution",
                    "container.namespace_delete_containerdistribution",
                    "container.namespace_view_containerdistribution",
                    "container.namespace_pull_containerdistribution",
                    "container.namespace_push_containerdistribution",
                    "container.namespace_change_containerdistribution",
                    "container.namespace_view_containerpushrepository",
                    "container.namespace_modify_content_containerpushrepository",
                ],
            },
            {
                "function": "create_namespace_group",
                "parameters": {
                    "group_type": "collaborators",
                    "add_user_to_group": False,
                },
                "permissions": [
                    "container.view_containernamespace",
                    "container.namespace_add_containerdistribution",
                    "container.namespace_delete_containerdistribution",
                    "container.namespace_view_containerdistribution",
                    "container.namespace_pull_containerdistribution",
                    "container.namespace_push_containerdistribution",
                    "container.namespace_change_containerdistribution",
                    "container.namespace_view_containerpushrepository",
                    "container.namespace_modify_content_containerpushrepository",
                ],
            },
            {
                "function": "create_namespace_group",
                "parameters": {
                    "group_type": "consumers",
                    "add_user_to_group": False,
                },
                "permissions": [
                    "container.view_containernamespace",
                    "container.namespace_view_containerdistribution",
                    "container.namespace_pull_containerdistribution",
                    "container.namespace_view_containerpushrepository",
                ],
            },
        ],
    }
}


def set_pulp_container_access_policy(apps, schema_editor):
    AccessPolicy = apps.get_model("core", "AccessPolicy")
    print(AccessPolicy)
    for view in viewsets:
        policy, created = AccessPolicy.objects.update_or_create(
            viewset_name=view, defaults={**viewsets[view], "customized": True})


class Migration(migrations.Migration):

    dependencies = [
        ('galaxy', '0017_populate_repos_and_remotes'),
    ]

    operations = [
        migrations.RunPython(
            code=set_pulp_container_access_policy,
        ),
    ]
