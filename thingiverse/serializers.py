from rest_framework import serializers
from .models import ObjetoThingi

class ThingiverseAPIKeyRequestSerializer(serializers.Serializer):
    uses = serializers.IntegerField(required=False)
    api_key = serializers.CharField(read_only=True)

class ObjetoThingiSerializer(serializers.ModelSerializer):
    class Meta:
        model = ObjetoThingi
        fields = '__all__'

    def create(self, validated_data):
        #Ejecutamos la tarea de celery
        print(validated_data)
        return ObjetoThingi.objects.create_object(**validated_data)
