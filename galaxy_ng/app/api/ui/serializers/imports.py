from rest_framework import serializers

from pulp_ansible.app.models import CollectionImport as PulpCollectionImport


class ImportTaskListSerializer(serializers.ModelSerializer):
    """
    A serializer for a CollectionImport list view.
    """

    id = serializers.UUIDField(source="pk")
    state = serializers.CharField(source="task.state")
    namespace = serializers.CharField(source="galaxy_import.namespace.name")
    name = serializers.CharField(source="galaxy_import.name")
    version = serializers.CharField(source="galaxy_import.version")
    created_at = serializers.DateTimeField(source="task.pulp_created")
    updated_at = serializers.DateTimeField(source="task.pulp_last_updated")
    started_at = serializers.DateTimeField(source="task.started_at")
    finished_at = serializers.DateTimeField(source="task.finished_at")

    class Meta:
        model = PulpCollectionImport
        fields = ("id", "state", "namespace", "name", "version",
                  "created_at", "updated_at", "started_at", "finished_at")


class ImportTaskDetailSerializer(ImportTaskListSerializer):

    error = serializers.JSONField(source="task.error")
    messages = serializers.JSONField()

    class Meta(ImportTaskListSerializer.Meta):
        fields = ImportTaskListSerializer.Meta.fields + \
            ('error', 'messages')
