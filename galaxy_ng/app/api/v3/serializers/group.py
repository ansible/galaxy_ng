from rest_framework import serializers


class GroupSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=False)
