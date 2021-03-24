from pulpcore.plugin import models as core_models


class ContainerAccessPolicyOverrides:
    def set_access_policy(self):
        for view in self.viewsets:
            policy = core_models.AccessPolicy.objects.get(viewset_name=view)
            policy.update(**self.viewsets[view], customized=True)

    viewsets = {
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
                    "principal": "autenticated",
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

        # TODO: as ina if these are used
        # "repositories/container/container-push": {
        #     "statements": {},
        #     "permissions_assignment": {}
        # },

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
        },
    }
