from rest_framework import serializers
from .models import Escaneo, Imagen, Identificador


class EscaneoSerializer(serializers.ModelSerializer):
    name_list = serializers.ListField(child=serializers.CharField(), required=False, write_only=True)
    amount = serializers.IntegerField(write_only=True)
    remaining_files = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Escaneo
        fields = ('id','name_list','amount','remaining_files')

    def create(self, validated_data):
        return Escaneo.objects.create_object(**validated_data)


class ImagenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Imagen
        fields = '__all__'


