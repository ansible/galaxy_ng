VIEWSETS = {
    "NamespaceViewSet": {
        "LOCKED_ROLES": {
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
        },
    },
    "SyncListViewSet": {
        "LOCKED_ROLES": {
            "galaxy.synclist_owner": [
                "galaxy.add_synclist",
                "galaxy.change_synclist",
                "galaxy.delete_synclist",
                "galaxy.view_synclist",
            ],
        }
    },
}
