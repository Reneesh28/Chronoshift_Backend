from rest_framework import serializers


class TimelineSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    description = serializers.CharField()