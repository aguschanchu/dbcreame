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
        #Hay que crear el modelo?
        if validated_data.get('update_object'):
                return ObjetoThingi.objects.update_object(**validated_data)
        else:
            return ObjetoThingi.objects.create_object(**validated_data)
