from rest_framework import serializers

class ThingiverseAPIKeyRequestSerializer(serializers.Serializer):
    uses = serializers.IntegerField(required=False)
    api_key = serializers.CharField(read_only=True)
