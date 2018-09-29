from rest_framework import serializers
from .models import ObjetoThingi

class ThingiverseAPIKeyRequestSerializer(serializers.Serializer):
    uses = serializers.IntegerField(required=False)
    api_key = serializers.CharField(read_only=True)

class ObjetoThingiSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    external_id = serializers.IntegerField()
    status = serializers.CharField(read_only=True)
    file_list = serializers.ListField(child=serializers.IntegerField())

    def create(self, validated_data):
        return ObjetoThingi.objects.get_or_create(external_id=validated_data.pop('external_id'))[0]
