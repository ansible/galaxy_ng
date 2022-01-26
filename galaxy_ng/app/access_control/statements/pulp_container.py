# These access policies are loaded via a post migration signal. To reload them after
# an edit, just rerun the migrations and any changes will get applied.

PULP_CONTAINER_VIEWSETS = {
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
                "condition_expression": [
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
                    "has_namespace_or_obj_perms:container.change_containerdistribution",
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
        # Removed permission assignement. Filtering out the container groups
        # proved to be too much of a challenge.
        "creation_hooks": []
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
                "condition": "has_model_perms:container.add_containernamespace",
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
        # Removed group creation for owner. Filtering out the container groups proved to be too
        # much of a challenge.
        "creation_hooks": [
            {
                "function": "add_for_object_creator",
                "parameters": None,
                "permissions": [
                    "container.view_containernamespace",
                    "container.delete_containernamespace",
                    # Add `container.change_containernamespace` permissions so the namespace
                    # owner can add additional groups to their namespace.
                    "container.change_containernamespace",
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
        ],
    },


    "repositories/container/container-push": {
        "statements": [
            {
                "action": ["list"],
                "principal": "authenticated",
                "effect": "allow",
            },
            {
                "action": ["retrieve"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_namespace_or_obj_perms:container.view_containerpushrepository",
            },
            {
                "action": ["tag", "untag", "remove_image"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": [
                    "has_namespace_or_obj_perms:container.modify_content_containerpushrepository",
                ],
            },
        ],
        # Remove permission assignment since it's trying to add permissions to groups
        # that don't exist
        "creation_hooks": [],
    }

}
