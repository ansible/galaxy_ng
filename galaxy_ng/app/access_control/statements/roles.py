VIEWSETS = {
    "CollectionViewSet": {
        "LOCKED_ROLES": {
            "galaxy.collection_admin": [
                "galaxy.change_namespace",
                "galaxy.delete_namespace",
                "galaxy.view_namespace",
                "galaxy.upload_to_namespace",
                "ansible.delete_collection",
            ],
        }
    },
    "ContainerRepositoryViewSet": {
        "LOCKED_ROLES": {
            "galaxy.execution_environment_admin": [
                "container.delete_containerrepository",
                "container.namespace_change_containerdistribution",
                "container.namespace_modify_content_containerpushrepository",
                "container.namespace_push_containerdistribution",
                "container.add_containernamespace",
                "container.change_containernamespace",
            ],
        }
    },
    "NamespaceViewSet": {
        "LOCKED_ROLES": {
            "galaxy.content_admin": [
                "ansible.modify_ansible_repo_content",
            ],
            "galaxy.namespace_owner": [
                "galaxy.add_namespace",
                "galaxy.change_namespace",
                "galaxy.delete_namespace",
                "galaxy.view_namespace",
                "galaxy.upload_to_namespace",
                "ansible.delete_collection",
            ],
            "galaxy.publisher": [
                "galaxy.upload_to_namespace",
                "ansible.delete_collection",
            ],
            "galaxy.group_admin": [
                "galaxy.view_group",
                "galaxy.delete_group",
                "galaxy.add_group",
                "galaxy.change_group",
            ],
            "galaxy.user_admin": [
                "galaxy.view_user",
                "galaxy.delete_user",
                "galaxy.add_user",
                "galaxy.change_user",
            ],
        },
    },
    "SyncListViewSet": {
        "LOCKED_ROLES": {
            "galaxy.synclist_owner": [
                "galaxy.add_synclist",
                "galaxy.change_synclist",
                "galaxy.delete_synclist",
                "galaxy.view_synclist",
                "ansible.change_collectionremote",
            ],
        }
    },
}
