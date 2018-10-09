from rest_framework import serializers
from vision.models import ImagenVisionAPI

class ImagenVisionAPISerializer(serializers.ModelSerializer):
    class Meta:
        model = ImagenVisionAPI
        fields = '__all__'

    def create(self, validated_data):
        return ImagenVisionAPI.objects.create_object(**validated_data)
