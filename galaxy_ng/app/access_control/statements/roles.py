VIEWSETS = {
    "NamespaceViewSet": {
        "LOCKED_ROLES": {
            "galaxy.namespace_creator": [
                "galaxy.add_namespace",
            ],
            "galaxy.namespace_owner": [
                "galaxy.add_namespace",
                "galaxy.change_namespace",
                "galaxy.delete_namespace",
            ],
            "galaxy.namespace_updater": [
                "galaxy.change_namespace",
            ],
        },
    },
    "ColletionViewSet": {
        "LOCKED_ROLES": {
            "galaxy.collection_delete": [
                "ansible.delete_collection",
            ],
            "galaxy.collection_mover": [
                "ansible.modify_ansible_repo_content",
            ],
        }
    },
}
