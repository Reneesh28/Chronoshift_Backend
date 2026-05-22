from rest_framework import serializers

class BranchCreateSerializer(serializers.Serializer):
    timeline_id = serializers.CharField(max_length=24)
    parent_branch_id = serializers.CharField(max_length=24, required=False, allow_null=True, allow_blank=True)
    decision = serializers.CharField(required=False, allow_blank=True)
    branch_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

class EventInjectSerializer(serializers.Serializer):
    timeline_id = serializers.CharField(max_length=24)
    branch_id = serializers.CharField(max_length=24)
    event_type = serializers.CharField(max_length=50, default="decision")
    decision = serializers.CharField(required=True)

class CompareBranchesSerializer(serializers.Serializer):
    timeline_id = serializers.CharField(max_length=24)
    branch_ids = serializers.ListField(
        child=serializers.CharField(max_length=24),
        min_length=1
    )
