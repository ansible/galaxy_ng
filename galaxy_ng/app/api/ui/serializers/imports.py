from rest_framework import serializers


class ImportTaskListSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    state = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        task_obj = self.context['task_obj']
        data.update({
            'namespace': task_obj.namespace.name,
            'name': task_obj.name,
            'version': task_obj.version,
        })
        return data


class ImportTaskDetailSerializer(ImportTaskListSerializer):

    error = serializers.JSONField()
    messages = serializers.JSONField()
