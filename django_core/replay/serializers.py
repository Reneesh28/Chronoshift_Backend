from rest_framework import serializers

class ReplayStartSerializer(serializers.Serializer):
    timeline_id = serializers.CharField(max_length=24)
    branch_id = serializers.CharField(max_length=24)
