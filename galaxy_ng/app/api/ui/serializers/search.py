from rest_framework import serializers


class SearchResultsSerializer(serializers.Serializer):
    name = serializers.CharField()
    namespace = serializers.CharField(source="namespace_name")
    description = serializers.CharField(source="description_text")
    type = serializers.CharField(source="content_type")
    latest_version = serializers.CharField()
    avatar_url = serializers.CharField(source="namespace_avatar")
    contents = serializers.JSONField(source="content_list")
    download_count = serializers.IntegerField()
    last_updated = serializers.DateTimeField()
    deprecated = serializers.BooleanField()
    tags = serializers.JSONField(source="tag_names")
    platforms = serializers.JSONField(source="platform_names")
    relevance = serializers.FloatField()
    search = serializers.CharField()
