from galaxy_ng.app.access_control.statements.standalone import (
    _collection_statements,
    _group_statements,
)


def _add_default(statements):
    """
    Converts a list of statements into a pulp access policy.
    """
    return {
        "statements": statements,
        "creation_hooks": None,
        "queryset_scoping": {"function": "scope_queryset"},
    }


_deny_all = _add_default([
    {
        "principal": "*",
        "action": "*",
        "effect": "deny"
    },
])


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
        "creation_hooks": []
    },

    "pulp_container/namespaces": {
        "statements": [
            {
                "action": ["list", "my_permissions"],
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
            {
                "action": ["list_roles", "add_role", "remove_role"],
                "principal": "authenticated",
                "effect": "allow",
                "condition": "has_model_or_obj_perms:container.manage_roles_containernamespace",
            },
        ],
        "creation_hooks": [
            {
                "function": "add_roles_for_object_creator",
                "parameters": {
                    "roles": [
                        "galaxy.execution_environment_namespace_owner",
                    ],
                },
            }
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
                "action": ["tag", "untag", "remove_image", "sign", "remove_signatures"],
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


PULP_ANSIBLE_VIEWSETS = {
    'pulp_ansible/v3/collections': _add_default(_collection_statements),
    'pulp_ansible/v3/collection-versions': _add_default(_collection_statements),
    'pulp_ansible/v3/collection-versions/docs': _add_default(_collection_statements),
    'pulp_ansible/v3/collections/imports': _add_default(_collection_statements),
    'pulp_ansible/v3/repo-metadata': _add_default(_collection_statements),

    'repositories/ansible/ansible': _add_default([
        {
            "action": ["retrieve", "my_permissions", "list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.view_ansiblerepository"
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:ansible.add_ansiblerepository"
        },
        {
            "action": [
                "copy_collection_version",
                "move_collection_version",
                "modify",
                "update",
                "partial_update",
                "sync",
                "rebuild_metadata",
                "sign",
                "mark",
                "unmark"
            ],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.change_ansiblerepository"
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.delete_ansiblerepository"
        },
        {
            "action": ["list_roles", "add_role", "remove_role"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.manage_roles_ansiblerepository",
        },
    ]),

    "distributions/ansible/ansible": _add_default([
        {
            "action": "retrieve",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distribution_repo_perms:ansible.view_ansiblerepository"
        },
        {
            "action": "list",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distribution_repo_perms:ansible.view_ansiblerepository"
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distribution_repo_perms:ansible.add_ansiblerepository"
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distribution_repo_perms:ansible.change_ansiblerepository"
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_distribution_repo_perms:ansible.delete_ansiblerepository"
        },
    ]),

    'remotes/ansible/collection': _add_default([
        {
            "action": ["retrieve", "my_permissions", "list"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.view_collectionremote"
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_perms:ansible.add_collectionremote"
        },
        {
            "action": "update",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.change_collectionremote"
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.delete_collectionremote"
        },
        {
            "action": ["list_roles", "add_role", "remove_role"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_model_or_obj_perms:ansible.manage_roles_collectionremote",
        },
    ]),

    'repositories/ansible/ansible/versions': _add_default([
        {
            "action": "retrieve",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_repository_model_or_obj_perms:ansible.view_ansiblerepository"
        },
        {
            "action": "list",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_repository_model_or_obj_perms:ansible.view_ansiblerepository"
        },
        {
            "action": "create",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_repository_model_or_obj_perms:ansible.add_ansiblerepository"
        },
        {
            "action": ["rebuild_metadata", "repair"],
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_repository_model_or_obj_perms:ansible.change_ansiblerepository"
        },
        {
            "action": "destroy",
            "principal": "authenticated",
            "effect": "allow",
            "condition": "has_repository_model_or_obj_perms:ansible.delete_ansiblerepository"
        },
    ]),

    # The following endpoints are related to issue https://issues.redhat.com/browse/AAH-224
    # For now endpoints are temporary deactivated
    'pulp_ansible/v3/collection-versions/all': _deny_all,
    'pulp_ansible/v3/collections/all': _deny_all,

    # disable upload and download APIs since we're not using them yet
    'pulp_ansible/v3/collections/upload': _deny_all,
    'pulp_ansible/v3/collections/download': _deny_all,

    'pulp_ansible/v3/legacy-redirected-viewset': _add_default([
        {
            "action": "*",
            "principal": "authenticated",
            "effect": "allow",
        },

        # we need the redirect in order to support anonymous downloads when the options are enabled
        {
            "action": "*",
            "principal": "anonymous",
            "effect": "allow",
        }
    ]),
}

PULP_CORE_VIEWSETS = {
    'groups/roles': _add_default(_group_statements),
    'roles': _add_default([
        {
            "action": ["list"],
            "principal": "authenticated",
            "effect": "allow",
        },
        {
            "action": "*",
            "principal": "admin",
            "effect": "allow"
        }
    ])
}

PULP_VIEWSETS = {**PULP_CONTAINER_VIEWSETS, **PULP_ANSIBLE_VIEWSETS, **PULP_CORE_VIEWSETS}
